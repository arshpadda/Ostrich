import pytest
from tortoise import Tortoise


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://:memory:")

    from src.controlplane.db import TORTOISE_ORM

    TORTOISE_ORM["connections"]["default"] = "sqlite://:memory:"

    # Init via TORTOISE_ORM so alias is "default" as expected by models
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

    yield

    await Tortoise._drop_databases()
    await Tortoise.close_connections()
