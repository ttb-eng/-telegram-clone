import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_user
from app.models.user import User
from app.schemas.message import MessageSend, MessageResponse, ReadReceiptResponse
from app.services import message as msg_service
from app.services import user as user_service

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.post("", status_code=201, response_model=MessageResponse)
async def send_message(
    data: MessageSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    if data.receiver_username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")
    receiver = await user_service.get_user_by_username(db, data.receiver_username)
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    msg = await msg_service.create_message(db, current_user, receiver, data.content, data.msg_type)
    resp = MessageResponse.model_validate(msg)
    resp.sender_username = current_user.username
    resp.sender_display_name = current_user.display_name
    return resp


@router.get("/{peer_id}", response_model=list[MessageResponse])
async def get_chat_history(
    peer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    try:
        pid = uuid.UUID(peer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid peer ID")

    peer = await user_service.get_user_by_id(db, pid)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    messages, total = await msg_service.get_chat_history(
        db, current_user.id, pid, page, page_size
    )
    items = []
    for m in reversed(messages):
        resp = MessageResponse.model_validate(m)
        if m.sender_id == current_user.id:
            resp.sender_username = current_user.username
            resp.sender_display_name = current_user.display_name
        else:
            resp.sender_username = peer.username
            resp.sender_display_name = peer.display_name
        items.append(resp)
    return items


@router.post("/read/{peer_id}", response_model=ReadReceiptResponse)
async def mark_read(
    peer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    try:
        pid = uuid.UUID(peer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid peer ID")
    messages = await msg_service.mark_messages_read(db, current_user.id, pid)
    return ReadReceiptResponse(message_ids=[m.id for m in messages])


@router.post("/{message_id}/recall", response_model=MessageResponse)
async def recall_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    try:
        mid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID")
    try:
        msg = await msg_service.recall_message(db, mid, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MessageResponse.model_validate(msg)


@router.get("/search/all", response_model=dict)
async def search_messages(
    q: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    messages, total = await msg_service.search_messages(
        db, current_user.id, q, page, page_size
    )
    items = []
    for m in messages:
        resp = MessageResponse.model_validate(m)
        if m.sender_id == current_user.id:
            resp.sender_username = current_user.username
            resp.sender_display_name = current_user.display_name
        else:
            sender = await user_service.get_user_by_id(db, m.sender_id)
            if sender:
                resp.sender_username = sender.username
                resp.sender_display_name = sender.display_name
        items.append(resp)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
