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
