from pydantic import BaseModel, ConfigDict
from tortoise.contrib.pydantic import pydantic_model_creator

from .models import ChatMessage, User

# Create Pydantic schemas from Tortoise models
UserCreate = pydantic_model_creator(User, name="UserCreate", exclude_readonly=True, exclude=("firebase_uid",))
UserRead = pydantic_model_creator(User, name="UserRead")
UserUpdate = pydantic_model_creator(User, name="UserUpdate", exclude_readonly=True, exclude=("firebase_uid", "email"))

ChatMessageRead = pydantic_model_creator(ChatMessage, name="ChatMessageRead")


class ChatMessageCreate(BaseModel):
    content: str
    model_config = ConfigDict(from_attributes=True)
