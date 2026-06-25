import urllib.parse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgres://postgres:postgres@localhost:5433/ostrich"
    REDIS_URL: str = "redis://localhost:6380"
    USE_LOCAL_SANDBOX: bool = True
    GEMINI_API_KEY: str = ""
    # When True, Tortoise auto-creates/alters tables on startup. Keep False in
    # production so Aerich migrations own the schema; enable only for tests.
    GENERATE_SCHEMAS: bool = False

    model_config = {"env_file": "../.env", "extra": "ignore"}


settings = Settings()

connections = {"default": settings.DATABASE_URL}

parsed = urllib.parse.urlparse(settings.DATABASE_URL)
if parsed.query:
    query_params = urllib.parse.parse_qs(parsed.query)
    if "host" in query_params:
        connections["default"] = {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "user": parsed.username,
                "password": parsed.password,
                "database": parsed.path.lstrip("/"),
                "host": query_params["host"][0],
            },
        }

TORTOISE_ORM = {
    "connections": connections,
    "apps": {
        "models": {
            "models": ["src.controlplane.database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
