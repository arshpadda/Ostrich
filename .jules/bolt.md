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

## 2026-06-26 - Composite Indexes for Filter and Sort Queries
**Learning:** Queries that filter on one column (e.g. `user_id`) and sort on another (e.g. `created_at`) can suffer from performance issues if they don't have a composite index. While single-column indexes might exist, a composite index spanning both the filter and sort columns prevents expensive in-memory sorts and sequential scans on large datasets.
**Action:** Always add a composite index (e.g. `indexes = (("user_id", "created_at"),)`) to models when there is a frequent access pattern involving filtering by one field and ordering by another, especially when bounding the query with limits and offsets.

## 2026-06-30 - Prevent O(N) Re-renders During WebSocket Streaming
**Learning:** In a chat interface where messages are stored in an array (e.g., `messages`) and rendered iteratively, streaming tokens via WebSocket causes the array reference or individual objects to update rapidly. Without memoization, every token update forces *all* previously rendered message components to re-render, resulting in O(N) rendering performance cost during streaming.
**Action:** Always wrap components rendered in long lists (like `MessageBubble`) with `React.memo()`. This ensures that only the currently streaming message (whose props change) re-renders, while older messages bypass the render cycle.

## 2026-07-05 - Prevent O(N) Re-renders of Sub-components During Streaming
**Learning:** In a chat interface with streaming WebSocket tokens, wrapping the parent message container (e.g., `MessageBubble`) in `React.memo` prevents re-rendering older messages. However, *within* the currently streaming message, any child components (like `ToolCallCard` or `CodeBlock`) will re-render on every token update unless they too are memoized. This causes unnecessary O(N) layout calculations and expensive syntax highlighting for elements that have already finished generating within the active message.
**Action:** Always wrap sub-components rendered within a streaming parent component (like `ToolCallCard` and `CodeBlock`) in `React.memo()`. This ensures that only the text node currently receiving tokens re-renders, while previously completed sub-components within the same message bypass the render cycle.
