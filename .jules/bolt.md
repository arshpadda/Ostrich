## 2024-05-18 - FastAPI Healthcheck Optimization\n**Learning:** In FastAPI, simple static endpoints (like healthchecks) defined as synchronous `def` incur unnecessary overhead by being dispatched to an external threadpool. Since they perform no blocking I/O, this is a pure loss.\n**Action:** Always define pure-data or non-blocking FastAPI endpoints as `async def` to run them directly on the main event loop.

## 2024-05-19 - Tortoise-ORM Bulk Serialization Optimization
**Learning:** In Tortoise-ORM/Pydantic integrations, serializing lists using list comprehensions with `await Schema.from_tortoise_orm(model)` introduces sequential overhead for each item in the list, scaling linearly.
**Action:** For lists/querysets, always use `await Schema.from_queryset(queryset)` instead. It is specifically designed to perform bulk fetching and serialization much more efficiently.
