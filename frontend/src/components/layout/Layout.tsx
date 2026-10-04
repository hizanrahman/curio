import { Outlet, useLocation } from "react-router-dom";
import { Navbar } from "./Navbar";
import { Toaster } from "sonner";

export function Layout() {
  const location = useLocation();
  const isSessionPage = location.pathname.startsWith('/session/');

  return (
    <div className="relative flex min-h-screen flex-col">
      {!isSessionPage && <Navbar />}
      <div className="flex-1">
        <Outlet />
      </div>
      <Toaster
        position="top-center"
        theme="light"
        toastOptions={{
          className: "theme-card bg-surface text-ink",
          style: { borderColor: "var(--ink)", color: "var(--ink)", background: "var(--surface)" },
        }}
      />
    </div>
  );
}
