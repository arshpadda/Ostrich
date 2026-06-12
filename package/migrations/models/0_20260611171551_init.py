from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "first_name" VARCHAR(100),
    "last_name" VARCHAR(100),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_users_email_133a6f" ON "users" ("email");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztlm1v2jAQx79KlFdM6lCbUlpN0yRKmco0YGphm1pVkYmdYOHYaeKsRYjvPp/JAwkPG2"
    "iUTuobhP93F9/9zolvavoCExZVBxEJzQ/G1OTIJ+pPQT8yTBQEuQqCREOmHWPloRU0jGSI"
    "HKlEF7GIKAmTyAlpIKngSuUxYyAKRzlS7uVSzOljTGwpPCJHOpH7ByVTjskzidJlMLZdSh"
    "gu5Ekx7K11W04CrQ0G7avP2hO2G9qOYLHPc+9gIkeCZ+5xTHEVYsDmEU5CJAleKAOyTMpN"
    "pXnGSpBhTLJUcS5g4qKYAQzzoxtzBxgYeif4qX0yt8DjCA5oKZfAYjqbV5XXrFUTtmpeN2"
    "4qp/V3ukoRSS/URk3EnOlAJNE8VHPNQRIfUbbMsjlC4WqWWUAJp0p1PyBTQLtRM330bDPC"
    "PTlSS+vsbAPG740bTVJ5aZRCnev5ae8mJmtuA6Q5QpeGkbT1aguOxaidYCaoMpapSw4zfy"
    "P3QfPk+PgvaCqvtTS1rUiToR1gFoLeWKYsnZBAxTaSyzCvlEVSn6wGWowsEcVJaDX9s8uL"
    "/wKAVQ24x9kkae8Gvv12p3Xbb3S+QSV+FD0yjajRb4HF0uqkpFbqpVZkDzF+tPvXBiyNu1"
    "63Vf4qZ379OxNyQrEUNhdPNsILH8BUTcEUGhsHeMfGFiPfGnvQxurkYcZxxwuXMwhD5Iyf"
    "UIjtJYuwxDrfZZNv+WUFceTprgBbyDIZ+RokpM5o1TCYWDaOgyj3eTXzYJvLLcZBdbjKpz"
    "1p2EHHFw92eW+d1M5rF6f12oVy0ZlkyvmG09/u9v8w/v1SUzyktMVduxDyb0bAl75q9zIE"
    "wquxBcTE/f8EuJ9ZRXBJ+Ir77Mttr7tmSMlDSiAHXBV4j6kjjwxGI/nwOrFuoAhVF+6sFF"
    "6l0/hZ5tr82rssX0bwgEvF+KDXy+w3E9w9nQ=="
)
