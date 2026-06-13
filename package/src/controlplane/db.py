from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite://:memory:"


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
