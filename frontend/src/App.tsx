import { useAuth } from "./auth/AuthContext";
import { Login } from "./components/Login";
import { ChatView } from "./components/ChatView";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-zinc-500">
        Loading…
      </div>
    );
  }

  return user ? <ChatView /> : <Login />;
}
