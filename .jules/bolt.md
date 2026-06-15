## 2024-05-18 - FastAPI Healthcheck Optimization
**Learning:** In FastAPI, simple static endpoints (like healthchecks) defined as synchronous `def` incur unnecessary overhead by being dispatched to an external threadpool. Since they perform no blocking I/O, this is a pure loss.
**Action:** Always define pure-data or non-blocking FastAPI endpoints as `async def` to run them directly on the main event loop.

## 2024-05-18 - TortoiseORM List Serialization
**Learning:** When serializing a list of TortoiseORM models to Pydantic, using `Schema.from_tortoise_orm(obj)` in a list comprehension is slow as it instantiates full Python objects for every row sequentially. `.values()` with Pydantic kwargs unpacking can break due to nested relational validations required by `pydantic_model_creator`.
**Action:** The natively performant and robust way to serialize list of models in TortoiseORM is to explicitly generate a list schema using `pydantic_queryset_creator(Model)` and then use `await ListSchema.from_queryset(queryset)` directly.
