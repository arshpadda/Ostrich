from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgres://postgres:postgres@localhost:5433/ostrich"

settings = Settings()

TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": ["src.controlplane.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
