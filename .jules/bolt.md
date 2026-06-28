## 2024-05-18 - FastAPI Healthcheck Optimization\n**Learning:** In FastAPI, simple static endpoints (like healthchecks) defined as synchronous `def` incur unnecessary overhead by being dispatched to an external threadpool. Since they perform no blocking I/O, this is a pure loss.\n**Action:** Always define pure-data or non-blocking FastAPI endpoints as `async def` to run them directly on the main event loop.

## 2024-05-18 - Tortoise ORM Pydantic Serialization Optimization
**Learning:** In Tortoise ORM, resolving Pydantic schemas sequentially in an async list comprehension (e.g., `[await Schema.from_tortoise_orm(msg) for msg in messages]`) incurs significant Python-level async iteration overhead and can cause N+1 query problems.
**Action:** Always use `await Schema.from_queryset(queryset)` to execute the fetch and schema mapping in an optimized batch manner when serializing multiple models to Pydantic schemas.
## 2024-05-14 - Unblocking the FastAPI Event Loop and Redis Polling
**Learning:** Calling synchronous blocking functions (like `subprocess.Popen` or Kubernetes API calls in `provision_sandbox_pod`) directly inside a FastAPI `async def` endpoint blocks the entire main event loop, causing severe latency and freezing other concurrent requests. Additionally, using a `while True` loop with `pubsub.get_message` and `asyncio.sleep()` for Redis pubsub consumes unnecessary CPU cycles and increases message latency compared to native async iteration.
**Action:** Always use `await asyncio.to_thread(func, args)` when calling blocking synchronous code from an async endpoint. For Redis pubsub, always use `async for message in pubsub.listen():` to leverage native async waiting and completely avoid sleep-based polling.

## 2026-06-18 - Unblocking the FastAPI Event Loop in WebSocket While Loop
**Learning:** Calling synchronous blocking functions (like `subprocess.Popen` or Kubernetes API calls in `provision_sandbox_pod`) directly inside a FastAPI `websocket_endpoint`'s `while True` loop blocks the entire main event loop when the connection receives a message, causing severe latency and freezing other concurrent requests.
**Action:** Always use `await asyncio.to_thread(func, args)` when calling blocking synchronous code from an async endpoint, even inside a WebSocket `while True` loop that runs after the connection is established.

## 2026-06-19 - Prevent DOM Layout Thrashing in List Rendering
**Learning:** Iteratively appending elements to the DOM and reading layout properties like `scrollHeight` synchronously causes forced reflows (layout thrashing) equal to the number of iterations (O(N) layout thrashing).
**Action:** Batch DOM updates using `DocumentFragment` and read/write layout properties only once after appending the fragment to the DOM.

## 2026-06-20 - Unblocking the FastAPI Event Loop in Auth Dependency
**Learning:** Calling synchronous blocking functions (like `auth.verify_id_token` for Firebase authentication) directly inside an `async def` function or dependency blocks the entire main event loop, causing latency and freezing other concurrent requests during authentication.
**Action:** Always use `await asyncio.to_thread(func, args)` when calling blocking synchronous authentication or network code from an async dependency or endpoint.

## 2026-06-21 - Database Query Optimization for Filtering and Sorting
**Learning:** Queries that filter by one column and sort by another (e.g., `filter(user=user_obj).order_by("created_at")`) can suffer from inefficient index scans or table scans if they rely on single-column indexes, especially as the table grows.
**Action:** Always add a composite index (e.g., `("user_id", "created_at")`) that covers both the filtering criteria and the sorting criteria to enable efficient queries for pagination and list retrieval.
