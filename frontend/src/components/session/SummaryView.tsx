import { useEffect, useState } from "react";
import { useTutorStore } from "@/store/useTutorStore";
import { CheckCircle2, AlertTriangle, ArrowRight, BookOpen } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL, authorizedFetch } from "@/lib/api";
import { ThemeButton } from "@/components/theme/ThemeButton";
import { ThemeCard } from "@/components/theme/ThemeCard";
import { StatusPill } from "@/components/theme/StatusPill";
import { IndependenceRing } from "@/components/theme/IndependenceRing";
import { StatChip } from "@/components/theme/StatChip";
import { Lightbulb, Sparkles, Target } from "lucide-react";

export function SummaryView() {
  const { concepts, misconceptions, helpDependence, messages, rewardPoints, sessionId, transferProblem, completionKind } = useTutorStore();
  const reset = useTutorStore(state => state.reset);
  const setSession = useTutorStore(state => state.setSession);
  const navigate = useNavigate();
  const [totalPoints, setTotalPoints] = useState<number | null>(null);
  const [isStartingTransfer, setIsStartingTransfer] = useState(false);
  const [transferError, setTransferError] = useState("");

  useEffect(() => {
    let active = true;
    void authorizedFetch(`${API_BASE_URL}/api/rewards/balance`)
      .then(response => {
        if (!response.ok) throw new Error("Could not load reward balance.");
        return response.json();
      })
      .then(data => {
        if (active) setTotalPoints(data.points);
      })
      .catch(error => console.error(error));
    return () => { active = false; };
  }, []);
  
  const userSteps = messages.filter(m => m.role === 'user').length;
  const avgHints = userSteps > 0 ? (helpDependence / userSteps).toFixed(1) : 0;
  const independence = Math.round(Math.max(0, Math.min(100, (1 - Number(avgHints)) * 100)));
  
  const masteredConcepts = concepts.filter(c => c.status === 'mastered');
  const needsPractice = concepts.filter(c => c.status === 'needs_practice');

  const handleTransfer = async () => {
    if (!sessionId) return;
    setIsStartingTransfer(true);
    setTransferError("");
    try {
      const response = await authorizedFetch(`${API_BASE_URL}/api/sessions/${sessionId}/transfer`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Could not start the transfer problem.");
      }
      const data = await response.json();
      setSession(
        data.session_id,
        data.problem_text,
        data.concepts,
        data.mode,
        data.problem_type,
        data.transfer_problem,
        data.concept_links,
        data.learning_objective,
      );
      navigate(`/session/${data.session_id}`);
    } catch (error) {
      setTransferError(error instanceof Error ? error.message : "Could not start the transfer problem.");
    } finally {
      setIsStartingTransfer(false);
    }
  };

  return (
    <main className="page-shell max-w-5xl space-y-8 py-10">
      <div className="relative mx-auto max-w-2xl space-y-3 text-center">
        <div className="solved-confetti pointer-events-none absolute inset-x-0 top-0 h-14 overflow-hidden" aria-hidden="true">
          {Array.from({ length: 6 }, (_, index) => <span key={index} className="solved-confetti-piece" />)}
        </div>
        <span className="sticker-chip inline-flex -rotate-2 items-center gap-2 bg-mint"><Sparkles aria-hidden="true" className="h-4 w-4" /> BIG BRAIN MOMENT</span>
        <h1 className="flex flex-wrap items-center justify-center gap-2 text-4xl font-extrabold sm:text-5xl">
          <CheckCircle2 aria-hidden="true" className="h-9 w-9 text-primary" />
          {completionKind === "verified" ? "Solved independently" : completionKind === "assisted" ? "Verified with support" : "Learning goal reached"}
        </h1>
        <p className="text-muted-foreground">
          {completionKind === "verified"
            ? "You didn&apos;t just finish a problem—you practiced how to think it through."
            : completionKind === "assisted"
              ? "Your result checks out. Keep building on what you learned."
              : "You demonstrated the key ideas for this question. Your learning map is complete."}
        </p>
      </div>

      <ThemeCard variant="white" className="flex flex-col items-center justify-between gap-6 p-5 sm:flex-row sm:p-7">
        <div className="flex flex-col items-center gap-3 sm:flex-row">
          <IndependenceRing score={independence} size={88} />
          <div className="text-center sm:text-left">
            <h2 className="font-display text-xl font-extrabold">Independence indicator</h2>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">A hint-frequency estimate for this session, not a grade.</p>
          </div>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <StatChip label="hints used" value={helpDependence} Icon={Lightbulb} />
          <StatChip label="steps tried" value={userSteps} Icon={Target} />
        </div>
      </ThemeCard>

      <ThemeCard variant="yellow" className="flex flex-col items-center gap-2 p-5 text-center sm:flex-row sm:justify-between sm:text-left">
        <div><p className="text-sm font-bold">Verified practice points</p><p className="text-xs text-ink/80">{rewardPoints > 0 ? `+${rewardPoints} for a verified result.` : "Points come from verified answers, not time spent."}</p></div>
        <p className="font-mono text-3xl font-extrabold">{totalPoints ?? "—"} <span className="text-sm">points</span></p>
      </ThemeCard>

      <div className="grid gap-5 md:grid-cols-2">
        <ThemeCard variant="mint" className="p-5 sm:p-6">
          <h2 className="mb-4 flex items-center gap-2 font-display text-xl font-extrabold">
            <BookOpen aria-hidden="true" className="h-5 w-5" /> Concepts demonstrated
          </h2>
          {masteredConcepts.length > 0 ? (
            <ul className="space-y-2">
              {masteredConcepts.map(c => (
                <li key={c.id} className="flex items-center justify-between gap-2 rounded-xl border-2 border-ink bg-surface p-3 text-sm font-semibold">
                  {c.name} <StatusPill status={c.status} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink/80">No concepts were formally marked mastered in this session.</p>
          )}
        </ThemeCard>

        <ThemeCard variant="coral" className="p-5 sm:p-6">
          <h2 className="mb-4 flex items-center gap-2 font-display text-xl font-extrabold">
            <AlertTriangle aria-hidden="true" className="h-5 w-5" /> Ideas to revisit
          </h2>
          {misconceptions.length > 0 || needsPractice.length > 0 ? (
            <ul className="space-y-3">
              {needsPractice.map(c => (
                <li key={c.id} className="text-sm">
                  <span className="flex items-center justify-between gap-2 rounded-xl border-2 border-ink bg-surface p-3 font-semibold">{c.name}<StatusPill status={c.status} /></span>
                </li>
              ))}
              {misconceptions.map(m => (
                <li key={m.id} className="rounded-xl border-2 border-ink bg-surface p-3 text-sm">
                  {m.description}
                  {m.count > 1 && <span className="block font-bold mt-1">Repeated {m.count} times.</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Great job! No major misconceptions caught.</p>
          )}
        </ThemeCard>
      </div>

      <ThemeCard variant="sky" className="p-5 sm:p-6">
        <h2 className="mb-2 font-display text-xl font-extrabold">Your hint rhythm</h2>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-3xl font-extrabold">{avgHints}</span>
          <span className="text-muted-foreground">hints per step</span>
        </div>
        <p className="mt-2 text-sm text-ink/80">
          {Number(avgHints) < 1 ? "You worked highly independently!" : "You relied heavily on hints. Try working more independently next time."}
        </p>
      </ThemeCard>

      <ThemeCard variant="lilac" className="p-5 sm:p-6">
        {transferProblem ? (
          <>
            <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold">
              <ArrowRight className="h-5 w-5 text-primary" /> Try a transfer problem
            </h2>
            <p className="mb-4 text-sm">Practice the same idea in a new context:</p>
            <div className="rounded-xl border-2 border-ink bg-surface p-4 text-center font-mono text-lg shadow-[var(--shadow-hard)]">
              {transferProblem}
            </div>
            <ThemeButton
              onClick={() => void handleTransfer()}
              disabled={isStartingTransfer}
              className="mt-4 w-full"
            >
              {isStartingTransfer ? "Preparing practice..." : "Practice this problem"}
            </ThemeButton>
            {transferError && <p role="alert" className="mt-2 text-sm text-destructive">{transferError}</p>}
          </>
        ) : (
          <>
            <h2 className="mb-2 text-lg font-semibold">Keep practicing</h2>
            <p className="text-sm text-muted-foreground">A related practice problem was not generated for this session.</p>
          </>
        )}
        <ThemeButton
          variant="secondary"
          onClick={() => {
            reset();
            navigate("/learn");
          }}
          className="mt-4 w-full"
        >
          Start a different problem
        </ThemeButton>
      </ThemeCard>
    </main>
  );
}
