# ruff: noqa: E501  (auto-generated migration; long SQL lines are expected)
from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chat_messages" ADD "in_reply_to" UUID;
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_chat_messag_in_repl_5d1b0c" ON "chat_messages" ("in_reply_to");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_chat_messag_in_repl_5d1b0c";
        ALTER TABLE "chat_messages" DROP COLUMN "in_reply_to";"""


MODELS_STATE = (
    "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"
    "ED1PJOhDf5udDD/wDlETo="
)
