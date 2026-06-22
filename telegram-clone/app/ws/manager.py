import asyncio
import json
import uuid
import logging
from collections import defaultdict

from fastapi import WebSocket


from app.services.auth import decode_access_token
from app.redis_client import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[uuid.UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id].append(websocket)
        await self._set_online(user_id, True)

    async def disconnect(self, user_id: uuid.UUID, websocket: WebSocket):
        ws_list = self.active_connections.get(user_id, [])
        if websocket in ws_list:
            ws_list.remove(websocket)
        if not self.active_connections.get(user_id):
            self.active_connections.pop(user_id, None)
            await self._set_online(user_id, False)

    async def send_personal(self, user_id: uuid.UUID, message: dict):
        ws_list = self.active_connections.get(user_id, [])
        for ws in ws_list:
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast_to_user(self, user_id: uuid.UUID, message: dict):
        await self.send_personal(user_id, message)

    async def send_group(self, group_id: uuid.UUID, message: dict, exclude_user_id: uuid.UUID | None = None):
        from app.redis_client import get_redis
        try:
            redis_conn = await get_redis()
            pattern = f"user:online:*"
            keys = await redis_conn.keys(pattern)
            online_users = set()
            for k in keys:
                uid_str = k.decode().split(":")[-1]
                online_users.add(uuid.UUID(uid_str))
        except Exception:
            online_users = set()

        # Send to group members who are online
        from app.database import async_session_factory
        from app.services.group import get_group_member_ids
        async with async_session_factory() as session:
            member_ids = await get_group_member_ids(session, group_id)
            for mid in member_ids:
                if exclude_user_id and mid == exclude_user_id:
                    continue
                if mid in online_users:
                    await self.send_personal(mid, message)

    async def _set_online(self, user_id: uuid.UUID, online: bool):
        try:
            redis_conn = await get_redis()
            key = f"user:online:{user_id}"
            if online:
                await redis_conn.set(key, "1", ex=300)
            else:
                await redis_conn.delete(key)
        except Exception as e:
            logger.warning(f"Redis error: {e}")

    async def get_online_status(self, user_id: uuid.UUID) -> bool:
        try:
            redis_conn = await get_redis()
            return await redis_conn.exists(f"user:online:{user_id}")
        except Exception:
            return False


manager = ConnectionManager()


async def handle_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user_id = decode_access_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(user_id, websocket)
    logger.info(f"User {user_id} connected via WebSocket")

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                redis_conn = await get_redis()
                await redis_conn.expire(f"user:online:{user_id}", 120)
                continue

            if msg_type == "message":
                payload = raw.get("payload", {})
                receiver_str = payload.get("receiver_id")
                group_str = payload.get("group_id")
                content = payload.get("content", "")
                msg_id = raw.get("msg_id", str(uuid.uuid4()))

                from app.database import async_session_factory
                from sqlalchemy import select
                from app.models.user import User

                async with async_session_factory() as session:
                    sender_result = await session.execute(select(User).where(User.id == user_id))
                    sender_user = sender_result.scalar_one_or_none()
                    if not sender_user:
                        continue

                    # Group message
                    if group_str:
                        group_uuid = uuid.UUID(group_str)
                        from app.services.message import create_group_message
                        msg = await create_group_message(session, sender_user, group_uuid, content, "text")

                        msg_payload = {
                            "type": "new_message",
                            "payload": {
                                "msg_id": str(msg.id),
                                "sender_id": str(user_id),
                                "group_id": group_str,
                                "content": content,
                                "sender_username": sender_user.username,
                                "sender_display_name": sender_user.display_name,
                                "created_at": msg.created_at.isoformat(),
                            },
                        }

                        await manager.send_group(group_uuid, msg_payload, exclude_user_id=user_id)

                        await websocket.send_json({
                            "type": "message_ack",
                            "payload": {"msg_id": msg_id, "status": "delivered"},
                        })
                        continue

                    # Private message
                    receiver_uuid = uuid.UUID(receiver_str) if receiver_str else None
                    if receiver_uuid:
                        from app.redis_client import get_redis
                        receiver_result = await session.execute(select(User).where(User.id == receiver_uuid))
                        receiver_user = receiver_result.scalar_one_or_none()

                        if sender_user and receiver_user:
                            from app.services.message import create_message
                            await create_message(session, sender_user, receiver_user, content, "text")

                            if receiver_user.username == 'ai_bot':
                                from app.services.deepseek import get_ai_reply_with_tools
                                from app.services.message import get_recent_context

                                recent_msgs = await get_recent_context(
                                    session, sender_user.id, receiver_user.id
                                )

                                context_messages = [
                                    {"role": "system", "content": "你是一个乐于助人的AI助手，回答简洁准确。请使用中文回复。"}
                                ]
                                for msg in recent_msgs:
                                    role = "user" if msg.sender_id == sender_user.id else "assistant"
                                    context_messages.append({"role": role, "content": msg.content})

                                full_reply = ""
                                async for chunk in get_ai_reply_with_tools(context_messages):
                                    full_reply += chunk

                                await create_message(session, receiver_user, sender_user, full_reply, "text")
                                ai_msg = {
                                    "type": "new_message",
                                    "payload": {
                                        "msg_id": str(uuid.uuid4()),
                                        "sender_id": str(receiver_user.id),
                                        "receiver_id": str(sender_user.id),
                                        "content": full_reply,
                                        "created_at": __import__("datetime").datetime.now().isoformat(),
                                    },
                                }
                                await manager.send_personal(sender_user.id, ai_msg)

                        msg_payload = {
                            "type": "new_message",
                            "payload": {
                                "msg_id": msg_id,
                                "sender_id": str(user_id),
                                "receiver_id": receiver_str,
                                "content": content,
                                "created_at": __import__("datetime").datetime.now().isoformat(),
                            },
                        }

                        online = await manager.get_online_status(receiver_uuid)
                        if online:
                            await manager.send_personal(receiver_uuid, msg_payload)
                        else:
                            try:
                                redis_conn = await get_redis()
                                await redis_conn.lpush(
                                    f"offline_messages:{receiver_uuid}",
                                    json.dumps(msg_payload, default=str),
                                )
                                await redis_conn.ltrim(f"offline_messages:{receiver_uuid}", 0, 999)
                            except Exception as e:
                                logger.warning(f"Failed to store offline message: {e}")

                        await websocket.send_json({
                            "type": "message_ack",
                            "payload": {"msg_id": msg_id, "status": "delivered"},
                        })

            elif msg_type == "typing":
                receiver_str = raw.get("receiver_id")
                if receiver_str:
                    await manager.send_personal(
                        uuid.UUID(receiver_str),
                        {"type": "typing", "sender_id": str(user_id)},)


    except Exception as e:
        logger.info(f"WebSocket disconnected for user {user_id}: {e}")
    finally:
        await manager.disconnect(user_id, websocket)
