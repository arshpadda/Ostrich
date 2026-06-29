// Backend base URL comes from VITE_API_URL (.env / .env.production).
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Derive the WebSocket origin from the HTTP base (http->ws, https->wss).
export const WS_URL = API_URL.replace(/^http/, "ws");
