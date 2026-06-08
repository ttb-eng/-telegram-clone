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
                content = payload.get("content", "")
                msg_id = raw.get("msg_id", str(uuid.uuid4()))

                receiver_uuid = uuid.UUID(receiver_str) if receiver_str else None
                if receiver_uuid:
                    from app.redis_client import get_redis

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
