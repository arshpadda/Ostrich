from tortoise import fields, models


class User(models.Model):
    id = fields.UUIDField(primary_key=True)
    firebase_uid = fields.CharField(max_length=128, unique=True, null=True, db_index=True)
    email = fields.CharField(max_length=255, unique=True, db_index=True)
    first_name = fields.CharField(max_length=100, null=True)
    last_name = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

    def __str__(self) -> str:
        return self.email

class ChatMessage(models.Model):
    id = fields.UUIDField(primary_key=True)
    user = fields.ForeignKeyField('models.User', related_name='messages')
    content = fields.TextField()
    is_bot = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message by {self.user_id} at {self.created_at}"
