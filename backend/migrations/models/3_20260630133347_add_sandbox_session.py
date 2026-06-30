# ruff: noqa: E501  (auto-generated migration; long SQL lines are expected)
from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "sandbox_sessions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "claim_name" VARCHAR(255) NOT NULL,
    "sandbox_name" VARCHAR(255),
    "status" VARCHAR(20) NOT NULL DEFAULT 'active',
    "error" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "released_at" TIMESTAMPTZ,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "sandbox_sessions" IS 'Durable record of a per-session sandbox claim, for audit and debugging.';
        ALTER TABLE "chat_messages" ADD "sandbox_session_id" UUID;
        ALTER TABLE "chat_messages" ADD CONSTRAINT "fk_chat_mes_sandbox__801c9911" FOREIGN KEY ("sandbox_session_id") REFERENCES "sandbox_sessions" ("id") ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS "idx_chat_messag_user_id_ca5ec7" ON "chat_messages" ("user_id", "created_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_chat_messag_user_id_ca5ec7";
        ALTER TABLE "chat_messages" DROP CONSTRAINT IF EXISTS "fk_chat_mes_sandbox__801c9911";
        ALTER TABLE "chat_messages" DROP COLUMN "sandbox_session_id";
        DROP TABLE IF EXISTS "sandbox_sessions";"""


MODELS_STATE = (
    "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"
)
