from tortoise.contrib.pydantic import pydantic_model_creator
from .models import User

# Schema for reading the user (includes id, created_at, etc.)
UserRead = pydantic_model_creator(User, name="UserRead")

# Schema for creating the user (excludes id, created_at, updated_at)
UserCreate = pydantic_model_creator(User, name="UserCreate", exclude_readonly=True)

# Schema for updating the user (optional fields)
UserUpdate = pydantic_model_creator(
    User, name="UserUpdate", exclude_readonly=True, optional=("email", "first_name", "last_name")
)
