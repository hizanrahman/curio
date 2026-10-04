import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL, authorizedFetch } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { AlertTriangle, Trash2 } from "lucide-react";
import { ThemeCard } from "@/components/theme/ThemeCard";
import { ThemeButton } from "@/components/theme/ThemeButton";
import { ProfileSettings } from "@/components/account/ProfileSettings";

export function AccountPage() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const email = session?.user.email ?? "";

  const handleDelete = async (event: FormEvent) => {
    event.preventDefault();
    setErrorMessage("");
    if (!supabase || confirmation !== "DELETE") {
      setErrorMessage("Type DELETE exactly to confirm account deletion.");
      return;
    }
    setIsBusy(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw new Error("Password verification failed. Please try again.");
      const response = await authorizedFetch(`${API_BASE_URL}/api/account`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm_email: email }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Account deletion failed.");
      }
      await supabase.auth.signOut({ scope: "local" });
      navigate("/", { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Account deletion failed.");
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <main className="page-shell max-w-3xl space-y-8 py-10">
      <div>
        <span className="sticker-chip inline-flex -rotate-2 bg-sky">YOUR DATA</span>
        <h1 className="mt-3 text-4xl font-extrabold">Account and data</h1>
        <p className="mt-2 text-muted-foreground">
          Your learning sessions are private to your account. You can permanently delete your account and saved sessions here.
        </p>
      </div>
      <ProfileSettings />
      <ThemeCard variant="coral" className="space-y-4 p-5 sm:p-7">
        <h2 className="flex items-center gap-2 font-display text-xl font-extrabold">
          <AlertTriangle aria-hidden="true" className="h-5 w-5" /> Delete account and learning data
        </h2>
        <p className="text-sm text-muted-foreground">
          This immediately deletes your account, sessions, tutor messages, and reward history. This cannot be undone.
        </p>
        <form onSubmit={event => void handleDelete(event)} className="space-y-4">
          <label className="block space-y-1 text-sm font-medium">
            Re-enter your password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={event => setPassword(event.target.value)}
              className="theme-input h-12 w-full px-3 font-normal"
            />
          </label>
          <label className="block space-y-1 text-sm font-medium">
            Type DELETE to confirm
            <input
              type="text"
              required
              value={confirmation}
              onChange={event => setConfirmation(event.target.value)}
              className="theme-input h-12 w-full px-3 font-normal"
            />
          </label>
          <ThemeButton
            type="submit"
            disabled={isBusy || confirmation !== "DELETE"}
            className="bg-destructive text-destructive-foreground"
          >
            <Trash2 aria-hidden="true" className="h-4 w-4" /> {isBusy ? "Deleting..." : "Permanently delete account"}
          </ThemeButton>
        </form>
        {errorMessage && <p role="alert" className="rounded-xl border-2 border-ink bg-surface p-3 text-sm font-semibold">{errorMessage}</p>}
      </ThemeCard>
    </main>
  );
}
