import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE_URL, authorizedFetch } from "@/lib/api";
import { ArrowRight, BookOpen, Sparkles } from "lucide-react";
import { EmptyState } from "@/components/theme/EmptyState";
import { StatChip } from "@/components/theme/StatChip";

interface LearningSession {
  id: string;
  problem_text: string;
  subject: string;
  topic: string;
  status: string;
  started_at: string;
  mode: string;
}

export function DashboardPage() {
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;
    void authorizedFetch(`${API_BASE_URL}/api/sessions`)
      .then(async response => {
        if (!response.ok) throw new Error("Could not load your learning history.");
        return response.json();
      })
      .then(data => {
        if (active) setSessions(data.sessions);
      })
      .catch(error => {
        if (active) setErrorMessage(error instanceof Error ? error.message : "Could not load your learning history.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, []);

  return (
    <main className="page-shell max-w-5xl space-y-8 py-9 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="sticker-chip inline-flex -rotate-2 items-center gap-2 bg-sky"><Sparkles aria-hidden="true" className="h-4 w-4" /> YOUR STUDY SPACE</span>
          <h1 className="mt-3 text-4xl font-extrabold sm:text-5xl">Look how far you&apos;ve thought.</h1>
          <p className="mt-3 text-muted-foreground">Pick up where you left off or take on a fresh question.</p>
        </div>
        <Link to="/learn" className="theme-button inline-flex min-h-11 items-center gap-2 bg-primary px-4 font-bold text-primary-foreground">
          New problem <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      </div>

      {!isLoading && !errorMessage && sessions.length > 0 && (
        <div className="flex flex-wrap gap-3">
          <StatChip label="sessions started" value={sessions.length} Icon={BookOpen} />
          <StatChip label="completed" value={sessions.filter(session => session.status === "completed").length} Icon={Sparkles} />
        </div>
      )}
      {isLoading && (
        <div className="space-y-3" aria-label="Loading your learning history">
          {[1, 2, 3].map(item => <div key={item} className="h-24 animate-pulse rounded-2xl border-2 border-ink bg-surface" />)}
        </div>
      )}
      {errorMessage && <p role="alert" className="rounded-xl border-2 border-ink bg-coral px-4 py-3 text-sm font-semibold">{errorMessage}</p>}
      {!isLoading && !errorMessage && sessions.length === 0 && (
        <EmptyState
          title="Your first “aha” is waiting."
          description="Start with a problem from class and work it through one thought at a time."
          illustration="book"
          action={<Link to="/learn" className="theme-button inline-flex min-h-11 items-center gap-2 bg-primary px-4 font-bold text-primary-foreground">Bring a problem <ArrowRight aria-hidden="true" className="h-4 w-4" /></Link>}
        />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {sessions.map(session => (
          <Link
            key={session.id}
            to={`/session/${session.id}`}
            className="theme-card theme-card-interactive group block bg-surface p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-display font-extrabold">{session.problem_text}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {session.subject} · {session.topic} · {session.mode}
                </p>
              </div>
              <span className={`inline-flex items-center gap-1.5 rounded-full border-2 border-ink px-3 py-1 text-xs font-bold capitalize ${session.status === "completed" ? "bg-mint" : "bg-yellow"}`}>
                {session.status === "completed" ? "✓" : "○"} {session.status}
              </span>
            </div>
            <time className="mt-3 block text-xs text-muted-foreground" dateTime={session.started_at}>
              {new Date(session.started_at).toLocaleString()}
            </time>
          </Link>
        ))}
      </div>
    </main>
  );
}
