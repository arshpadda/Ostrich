from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel, ConfigDict
from .models import User, ChatMessage

# Create Pydantic schemas from Tortoise models
UserCreate = pydantic_model_creator(User, name="UserCreate", exclude_readonly=True, exclude=("firebase_uid",))
UserRead = pydantic_model_creator(User, name="UserRead")
UserUpdate = pydantic_model_creator(User, name="UserUpdate", exclude_readonly=True, exclude=("firebase_uid", "email"))

ChatMessageRead = pydantic_model_creator(ChatMessage, name="ChatMessageRead")

class ChatMessageCreate(BaseModel):
    content: str
    model_config = ConfigDict(from_attributes=True)
