import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Flame } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { APP_NAME } from "@/config";

export function Navbar() {
  const { session } = useAuth();
  const [showStreakInfo, setShowStreakInfo] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b-2 border-ink bg-bg/95 backdrop-blur supports-[backdrop-filter]:bg-bg/85">
      <div className="page-shell flex min-h-16 items-center justify-between gap-3 py-2">
        <Link to="/" className="flex shrink-0 items-center gap-2 rounded-xl px-2 py-1">
          <span className="grid h-9 w-9 place-items-center rounded-xl border-2 border-ink bg-yellow shadow-[var(--shadow-hard)]">
            <BookOpen aria-hidden="true" className="h-5 w-5" />
          </span>
          <span className="font-display text-base font-extrabold sm:text-lg">{APP_NAME}</span>
        </Link>
        <nav aria-label="Main navigation" className="flex items-center gap-1 sm:gap-2">
          <Link to="/learn" className="theme-button hidden min-h-10 items-center gap-2 bg-primary px-3 text-sm font-bold text-primary-foreground md:inline-flex">
            Start Learning <ArrowRight aria-hidden="true" className="h-4 w-4" />
          </Link>
          {session ? (
            <>
              <div className="relative">
                <button
                  type="button"
                  className="inline-flex min-h-9 items-center justify-center rounded-full border-2 border-ink bg-yellow px-2.5"
                  aria-label="Streak tracking is currently paused. Show details."
                  aria-expanded={showStreakInfo}
                  aria-controls="streak-paused-details"
                  onClick={() => setShowStreakInfo(open => !open)}
                >
                  <Flame aria-hidden="true" className="h-4 w-4" /> 0
                </button>
                {showStreakInfo && (
                  <section
                    id="streak-paused-details"
                    aria-label="Streak status"
                    className="absolute right-0 top-full z-[60] mt-2 w-64 rounded-xl border-2 border-ink bg-surface p-4 text-left text-xs leading-relaxed text-ink shadow-[var(--shadow-hard)]"
                  >
                    <h2 className="font-display text-sm font-extrabold">Streaks are paused</h2>
                    <p className="mt-2">Streak tracking is temporarily unavailable while Daily Challenge is turned off.</p>
                    <button
                      type="button"
                      className="mt-3 min-h-9 rounded-lg px-2 font-bold underline underline-offset-2"
                      onClick={() => setShowStreakInfo(false)}
                    >
                      Got it
                    </button>
                  </section>
                )}
              </div>
              <Link to="/dashboard" className="hidden min-h-11 items-center rounded-xl px-2 text-xs font-bold hover:bg-secondary md:inline-flex md:px-3 md:text-sm">My learning</Link>
              <Link to="/learn" className="inline-flex min-h-11 items-center rounded-xl px-2 text-xs font-bold hover:bg-secondary sm:px-3 sm:text-sm">Learn</Link>
              <Link to="/account" className="hidden min-h-11 items-center rounded-xl px-3 text-sm font-bold hover:bg-secondary sm:inline-flex">Account</Link>
              <button
                onClick={() => void supabase?.auth.signOut()}
                className="inline-flex min-h-11 items-center rounded-xl px-2 text-xs font-bold hover:bg-secondary sm:px-3 sm:text-sm"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link to="/auth" className="theme-button inline-flex min-h-10 items-center bg-primary px-3 text-sm font-bold text-primary-foreground md:bg-surface md:text-ink">
              <span className="md:hidden">Start learning</span>
              <span className="hidden md:inline">Sign in</span>
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
