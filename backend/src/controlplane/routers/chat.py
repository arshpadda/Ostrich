from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import get_current_user
from ..database.models import ChatMessage, User
from ..database.schemas import ChatMessageCreate, ChatMessageRead

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/", response_model=List[ChatMessageRead])
async def list_messages(current_user: dict = Depends(get_current_user)):
    user_obj = await User.get_or_none(firebase_uid=current_user.get("uid"))
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    messages = await ChatMessage.filter(user=user_obj).order_by("created_at")
    return [await ChatMessageRead.from_tortoise_orm(msg) for msg in messages]


@router.post("/", response_model=ChatMessageRead, status_code=201)
async def create_message(message: ChatMessageCreate, current_user: dict = Depends(get_current_user)):
    user_obj = await User.get_or_none(firebase_uid=current_user.get("uid"))
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    msg_obj = await ChatMessage.create(user=user_obj, content=message.content, is_bot=False)

    return await ChatMessageRead.from_tortoise_orm(msg_obj)
