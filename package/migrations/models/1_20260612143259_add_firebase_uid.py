from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "firebase_uid" VARCHAR(128) UNIQUE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_users_firebas_6d1613";
        ALTER TABLE "users" DROP COLUMN "firebase_uid";"""


MODELS_STATE = (
    "eJztl21r2zAQx7+K8asOupC66QNjDNKH0Yw1Ga2zjZZiFEtxRGTJtaW1IeS7T6fYcew8LA"
    "59GvRNsP93Z939dLYuYzsUmLCk1k1IbH+yxjZHIdEXBX3XslEU5SoIEvWYcVTawyiol8gY"
    "+VKLfcQSoiVMEj+mkaSCa5UrxkAUvnakPMglxem9Ip4UAZEDk8jtnZYpx+SRJNltNPT6lD"
    "BcyJNiWNvonhxFRut2W2dfjScs1/N8wVTIc+9oJAeCz9yVorgGMWALCCcxkgTPlQFZpuVm"
    "0jRjLchYkVmqOBcw6SPFAIb9ua+4DwwssxL8NL7YFfD4ggNayiWwGE+mVeU1G9WGpU4vml"
    "c7+4cfTJUikUFsjIaIPTGBSKJpqOGag+zTmPRQQjy1DOnpAMXLkZbjSnB14htgTaFVoJrR"
    "2g6hHaJHjxEeyIG+3XOO1zD92bwyWLWX4Sp0k09bv52anKkN+OY8SYgoqwJyFrAVwS0a8y"
    "kROgcHGyDUXisRGlsRoW6tRHrmrlpDzkU9STtmLjnM/Av3LA1Zr2/SkPX66oYEW5EmQ1vA"
    "LAS9s8xY+jGBij0kF2GeaYukIVkOtBhZIorT0Fp2sc2L/wKAdQ24w9ko3d41fN3W5fm127"
    "z8AZWESXLPDKKmew4Wx6ijkrpzWNqK2UOsXy33woJb66bTPi+fcjM/98aGnJCSwuPiwUN4"
    "7gOYqRmYwsaqCG+5scXI94191Y01ycPM2B/ODTsg9JA/fEAx9hYswhGrfBdNoROWFcRRYH"
    "YF2EKW6QjdJDH1B/aS4Tq1rB2vUe7zZubrFpcVxmvdXOVuTzfsVceXAFb56Ow1jhrH+4eN"
    "Y+1iMpkpR2u6v9V2/zFO/9H/iiClCmftXMjTjIAvfdQ+yxAIr0YFiKn7/wnweWYVwSXhS8"
    "6zb9ed9oohJQ8pgexyXeAtpr7ctRhN5N3bxLqGIlRdOLMyeDuXzd9lrqffOyflwwgecKIZ"
    "v+rxMvkL+PupOw=="
)
