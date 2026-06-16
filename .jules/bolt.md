## 2024-05-18 - FastAPI Healthcheck Optimization\n**Learning:** In FastAPI, simple static endpoints (like healthchecks) defined as synchronous `def` incur unnecessary overhead by being dispatched to an external threadpool. Since they perform no blocking I/O, this is a pure loss.\n**Action:** Always define pure-data or non-blocking FastAPI endpoints as `async def` to run them directly on the main event loop.

## 2024-05-18 - Tortoise ORM Pydantic Serialization Optimization
**Learning:** In Tortoise ORM, resolving Pydantic schemas sequentially in an async list comprehension (e.g., `[await Schema.from_tortoise_orm(msg) for msg in messages]`) incurs significant Python-level async iteration overhead and can cause N+1 query problems.
**Action:** Always use `await Schema.from_queryset(queryset)` to execute the fetch and schema mapping in an optimized batch manner when serializing multiple models to Pydantic schemas.
