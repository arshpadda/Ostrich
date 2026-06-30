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


class SandboxSession(models.Model):
    """Durable record of a per-session sandbox claim, for audit and debugging.

    Maps a user's session to the agent-sandbox claim/pod that served it, with
    lifecycle timestamps. The kubernetes SandboxClaim is deleted on disconnect,
    so this table is the only lasting trail of which sandbox handled a session.
    """

    id = fields.UUIDField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="sandbox_sessions")
    claim_name = fields.CharField(max_length=255)
    sandbox_name = fields.CharField(max_length=255, null=True)  # resolved pod/channel key
    status = fields.CharField(max_length=20, default="active")  # active | released | failed
    error = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    released_at = fields.DatetimeField(null=True)

    class Meta:
        table = "sandbox_sessions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"SandboxSession {self.sandbox_name} ({self.status})"


class ChatMessage(models.Model):
    id = fields.UUIDField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="messages")
    # Which sandbox produced/handled this message (nullable for legacy rows).
    sandbox_session = fields.ForeignKeyField(
        "models.SandboxSession", related_name="messages", null=True, on_delete=fields.SET_NULL
    )
    content = fields.TextField()
    is_bot = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
        ordering = ["created_at"]
        # Performance Note (Bolt ⚡):
        # A composite index on user_id and created_at optimizes frequent access patterns
        # that filter by user and sort by time, preventing expensive sequential scans.
        indexes = (("user_id", "created_at"),)

    def __str__(self) -> str:
        return f"Message by {self.user_id} at {self.created_at}"
