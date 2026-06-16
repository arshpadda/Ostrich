import asyncio

from src.controlplane.db import TORTOISE_ORM
from src.controlplane.models import ChatMessage
from tortoise import Tortoise


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    msgs = await ChatMessage.all().order_by("-created_at").limit(5)
    for m in msgs:
        print(m.created_at, m.is_bot, m.content)


asyncio.run(main())
