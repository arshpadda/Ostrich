from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chat_messages" (
    "id" UUID NOT NULL PRIMARY KEY,
    "content" TEXT NOT NULL,
    "is_bot" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "chat_messages";"""


MODELS_STATE = (
    "eJztmVtv2jAUgP8KylMndRWltKumaVK4dGUtMNGwVa2qyMQGrDo2TZy1qOK/z3buIWHQUU"
    "onXhA5l8Tn88nxsfOs2Qwi4h7Ux4C3keuCEdI+l541Cmz5J0+9X9LAZBIrpYCDAVH2ljA0"
    "bd9SacDA5Q6wuFAOAXGREEHkWg6ecMyokFKPEClkljDEdBSLPIofPGRyNkJ8jByhuL0TYk"
    "whehI3Dy4n9+YQIwJTw8ZQPlvJTT6dKFm/32qcKUv5uIFpMeLZNLaeTPmY0cjc8zA8kD5S"
    "N0IUOYAjmAhDjjIIOxT5IxYC7ngoGiqMBRANgUckDO3L0KOWZFBST5I/1a/aCngsRiVaTL"
    "lk8Tzzo4pjVlJNPqp+rvf2jk4+qCiZy0eOUioi2kw5Ag58V8U1BikewhHl8zQN9MTzaSZc"
    "MkjFcF8CMxTENONMCnGGmNbOzmheG3LQtus+ECno/NR7Cmhbv1ZE7Wmguex2voXmTOS8/0"
    "Z06pfdmqKcSE/XHLAcqDXGCAK0IEsjpwzWgfB6La6rvrPLg611u5cpsLVWlly/XWv29g4V"
    "ZWGEuRK3OkYGp+UgGbYJcpA2hIZjGxXkasozwxUGrgfhn+1MXk3EALuUTIMysyiZW+3mla"
    "G3f6TAN3SjKTWVVDaH0j2/bsTTEt2k9KtlnJfkZemm22lmq0tkZ9xockzA48yk7NEEMFER"
    "Q2kIJjWxnoscc7VannBZZ0F/0xr0l/otV8HhfW75ljTm6Z0xB+ERvUBTxbAlxgGohXKYBc"
    "t/P7jN1lKLpXFmOeAx6gySaSHCE0Ehv5jU9au63mhqCuIAWPePwIFmiqbUsArLSCLbeZVd"
    "sbMSQEU/BIMo5JiTYHP6rRB4caMlA9o1WO+/wRpiBw2Ai0wvD6nou518pFm/F7VaAbQVqP"
    "7jUmWDJ5MgOuJjcXlYOV3ANGyzhFVmAQo7sIqvS/cCyAaYrAIyclhPs7pZhJXj4yUQCqtC"
    "hEqXRihSy+WmulotIRNea0nHDfRO6YQsl5dJyHK5OCGlLk2TgBfATDntWO4afe0/b/Qn8I"
    "UTm/bcTeybTqwa/Nx2pLi1TvS9iSPDzJlI4Hl20UMEKLTzE51/TLl9M120XZm95iZDRw62"
    "xlrONiPQLNxogNhma3YaLVpw9pjbC2P/MDKZDUHqvmkjp07aP1YOq5+qp0cn1VNhokYSST"
    "4tqAPhIVjxxuK32B8GL8uyXUfC5b2c3G6gHZavxgoQA/P3CfB1uraibwjfr7qdVb8h9KkI"
    "8BZii++XCHb53XZiXUBRRr34i0L240FmWZY3qOWd+23yDGv2ByxmEG8="
)
