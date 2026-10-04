import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { useAuth } from "@/lib/auth-context";
import { Layout } from "./components/layout/Layout";

const LandingPage = lazy(() => import("./pages/LandingPage").then(module => ({ default: module.LandingPage })));
const LearnPage = lazy(() => import("./pages/LearnPage").then(module => ({ default: module.LearnPage })));
const AuthPage = lazy(() => import("./pages/AuthPage").then(module => ({ default: module.AuthPage })));
const AccountPage = lazy(() => import("./pages/AccountPage").then(module => ({ default: module.AccountPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then(module => ({ default: module.DashboardPage })));
const SessionPage = lazy(() => import("./pages/SessionPage").then(module => ({ default: module.SessionPage })));

function PageLoading() {
  return (
    <div className="page-shell grid min-h-[70vh] place-items-center py-12" role="status">
      <div className="w-full max-w-xl animate-pulse rounded-2xl border-2 border-ink bg-surface p-8 text-center font-semibold text-muted-foreground">
        Getting your study space ready…
      </div>
    </div>
  );
}

function RequireAuth() {
  const { session, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  return session ? <Outlet /> : <Navigate to="/auth" replace />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-background font-sans text-foreground antialiased selection:bg-primary selection:text-primary-foreground">
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Suspense fallback={<PageLoading />}><LandingPage /></Suspense>} />
              <Route path="/auth" element={<Suspense fallback={<PageLoading />}><AuthPage /></Suspense>} />
              <Route element={<RequireAuth />}>
                <Route path="/dashboard" element={<Suspense fallback={<PageLoading />}><DashboardPage /></Suspense>} />
                <Route path="/learn" element={<Suspense fallback={<PageLoading />}><LearnPage /></Suspense>} />
                <Route
                  path="/session/:id"
                  element={
                    <Suspense fallback={<PageLoading />}>
                      <SessionPage />
                    </Suspense>
                  }
                />
                <Route path="/account" element={<Suspense fallback={<PageLoading />}><AccountPage /></Suspense>} />
              </Route>
            </Route>
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
