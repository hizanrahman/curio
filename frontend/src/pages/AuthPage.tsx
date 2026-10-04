import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { ArrowLeft, BookOpen, Sparkles } from "lucide-react";
import { ThemeButton } from "@/components/theme/ThemeButton";
import { ThemeCard } from "@/components/theme/ThemeCard";

export function AuthPage() {
  const { session, isLoading, isPasswordRecovery } = useAuth();
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resetEmailSent, setResetEmailSent] = useState(false);

  if (isLoading) return <p className="p-8 text-center text-muted-foreground">Checking sign-in...</p>;
  if (session && !isPasswordRecovery) return <Navigate to="/learn" replace />;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setMessage("");
    setErrorMessage("");
    if (!supabase) {
      setErrorMessage("Authentication is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (isPasswordRecovery) {
        const { error } = await supabase.auth.updateUser({ password });
        if (error) throw error;
        navigate("/learn", { replace: true });
      } else if (isSignUp) {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        if (data.session) navigate("/learn", { replace: true });
        else setMessage("Check your email to confirm your account, then sign in.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        navigate("/learn", { replace: true });
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePasswordReset = async () => {
    setErrorMessage("");
    setMessage("");
    if (!supabase || !email.trim()) {
      setErrorMessage("Enter your email address first.");
      return;
    }
    setIsSubmitting(true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: `${window.location.origin}/auth`,
      });
      if (error) throw error;
      setResetEmailSent(true);
      setMessage("If that account exists, a password reset link has been sent.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not send a reset link.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="page-shell flex min-h-[calc(100svh-4rem)] max-w-lg items-center justify-center py-10">
      <ThemeCard variant="white" className="w-full space-y-6 p-6 sm:p-8">
        <div>
          <span className="mb-4 grid h-12 w-12 place-items-center rounded-xl border-2 border-ink bg-yellow">
            <BookOpen aria-hidden="true" className="h-6 w-6" />
          </span>
          <h1 className="text-3xl font-extrabold">
            {isPasswordRecovery ? "Choose a new password" : isSignUp ? "Create your account" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">Sign in to save sessions and pick up your learning whenever you&apos;re ready.</p>
        </div>

        <form onSubmit={event => void handleSubmit(event)} className="space-y-4">
          {!isPasswordRecovery && (
            <label className="block space-y-1 text-sm font-medium">
              Email
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={event => setEmail(event.target.value)}
                className="theme-input h-12 w-full px-3 font-normal"
              />
            </label>
          )}
          <label className="block space-y-1 text-sm font-medium">
            Password
            <input
              type="password"
              autoComplete={isSignUp || isPasswordRecovery ? "new-password" : "current-password"}
              minLength={8}
              required
              value={password}
              onChange={event => setPassword(event.target.value)}
              className="theme-input h-12 w-full px-3 font-normal"
            />
          </label>
          <ThemeButton
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? "Please wait..." : isPasswordRecovery ? "Update password" : isSignUp ? "Create account" : "Sign in"} <Sparkles aria-hidden="true" className="h-4 w-4" />
          </ThemeButton>
        </form>

        {!isSignUp && !isPasswordRecovery && (
          <button
            type="button"
            onClick={() => void handlePasswordReset()}
            disabled={isSubmitting || resetEmailSent}
            className="w-full rounded-lg py-2 text-sm font-semibold text-primary underline underline-offset-4 disabled:opacity-50"
          >
            Forgot password?
          </button>
        )}

        {isSignUp && (
          <p className="text-xs text-muted-foreground">
            Your problem text and tutoring messages are saved to your account. Uploaded images/PDF pages may be sent to the configured AI provider for text extraction. Avoid personal details; if you are under 18, ask a parent or guardian before using this service.
          </p>
        )}

        {message && <p role="status" className="rounded-xl border-2 border-ink bg-mint p-3 text-sm font-semibold">{message}</p>}
        {errorMessage && <p role="alert" className="rounded-xl border-2 border-ink bg-coral p-3 text-sm font-semibold">{errorMessage}</p>}

        <p className="text-center text-sm text-muted-foreground">
          {isSignUp ? "Already have an account?" : "New here?"}{" "}
          <button
            type="button"
            className="font-bold text-primary underline underline-offset-4"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setMessage("");
              setErrorMessage("");
            }}
          >
            {isSignUp ? "Sign in" : "Create an account"}
          </button>
        </p>
        <p className="text-center text-xs text-muted-foreground">
          <Link to="/" className="inline-flex items-center justify-center gap-1 font-semibold underline underline-offset-4"><ArrowLeft aria-hidden="true" className="h-3.5 w-3.5" /> Back to home</Link>
        </p>
      </ThemeCard>
    </main>
  );
}
