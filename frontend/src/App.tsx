import { lazy, Suspense } from "react";
import { useAuth } from "./auth/AuthContext";
import { Login } from "./components/Login";

// Performance Note (Bolt ⚡):
// Code-split the ChatView component so that unauthenticated users only loading
// the Login page do not have to download the large ChatView and its dependencies.
const ChatView = lazy(() => import("./components/ChatView").then(m => ({ default: m.ChatView })));

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-zinc-500">
        Loading…
      </div>
    );
  }

  return user ? (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center text-sm text-zinc-500">
          Loading…
        </div>
      }
    >
      <ChatView />
    </Suspense>
  ) : <Login />;
}
