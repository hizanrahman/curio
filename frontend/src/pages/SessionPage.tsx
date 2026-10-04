import { lazy, Suspense, useState, useRef, useEffect } from "react";
import { useTutorStore, type Concept, type Message, type Misconception, type ProblemType, type TutorMode } from "@/store/useTutorStore";
import { HintMeter } from "@/components/session/HintMeter";
import { StepLadder } from "@/components/session/StepLadder";
import { ModeSelector } from "@/components/session/ModeSelector";
import { MathInput } from "@/components/session/MathInput";
import { SummaryView } from "@/components/session/SummaryView";
import { API_BASE_URL, authorizedFetch } from "@/lib/api";
import { Link, useParams } from "react-router-dom";
import { BookOpen, Lightbulb, Map, MessageCircle, Plus, Send, Sparkles, Target } from "lucide-react";
import { ThemeCard } from "@/components/theme/ThemeCard";
import { ThemeButton } from "@/components/theme/ThemeButton";
import { StatusPill } from "@/components/theme/StatusPill";
import { IndependenceRing } from "@/components/theme/IndependenceRing";
import { StatChip } from "@/components/theme/StatChip";
import { EmptyState } from "@/components/theme/EmptyState";
import ReactMarkdown from 'react-markdown';
import { motion, useReducedMotion } from "framer-motion";
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const ConceptMap = lazy(() => import("@/components/concepts/ConceptMap").then(module => ({ default: module.ConceptMap })));
const CodeEditor = lazy(() => import("@/components/session/CodeEditor").then(module => ({ default: module.CodeEditor })));

export function SessionPage() {
  const { id: sessionId } = useParams();
  const { messages, addMessage, problemText, problemType, mode, isCompleted, concepts, learningObjective, helpDependence, completeSession, updateConcept, addMisconception, incrementHelpDependence, setRewardPoints } = useTutorStore();
  const shouldReduceMotion = useReducedMotion();
  const [inputValue, setInputValue] = useState("");
  const [sessionError, setSessionError] = useState("");
  const [sendError, setSendError] = useState("");
  const [mobileTab, setMobileTab] = useState<"problem" | "tutor" | "map" | "progress">("tutor");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(
    () => sessionId !== useTutorStore.getState().sessionId,
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId || sessionId === useTutorStore.getState().sessionId) {
      return;
    }
    let active = true;
    void authorizedFetch(`${API_BASE_URL}/api/sessions/${sessionId}`)
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 404 ? "Session not found." : "Unable to restore this session.");
        return response.json();
      })
      .then(data => {
        if (!active) return;
        const messages: Message[] = data.messages.map((message: {
          id: string;
          role: "user" | "tutor";
          content: string;
          hint_level: number;
        }) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          hintLevel: message.hint_level,
          isStep: message.role === "user",
        }));
        useTutorStore.getState().restoreSession(
          sessionId,
          data.session.problem_text,
          data.concepts as Concept[],
          data.misconceptions as Misconception[],
          data.session.mode as TutorMode,
          data.session.problem_type as ProblemType,
          messages,
          data.reward_points,
          data.transfer_problem,
          data.concept_links,
          data.learning_objective,
        );
        if (data.session.status === "completed") {
          useTutorStore.getState().completeSession(
            data.session.completion_kind === "independent_solve"
              ? "verified"
              : data.session.completion_kind === "assisted_solve"
                ? "assisted"
                : "learning_goal",
          );
        }
      })
      .catch(error => {
        if (active) setSessionError(error instanceof Error ? error.message : "Unable to restore this session.");
      })
      .finally(() => {
        if (active) setIsLoadingSession(false);
      });
    return () => { active = false; };
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async () => {
    if (!inputValue.trim()) return;

    addMessage({ role: 'user', content: inputValue, isStep: true });
    const submittedInput = inputValue;
    setInputValue("");
    setSendError("");
    setIsSending(true);

    try {
      if (!sessionId) throw new Error("This session link is missing its session ID. Start a new session.");
      const res = await authorizedFetch(`${API_BASE_URL}/api/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: submittedInput,
          hint_level: Math.min(useTutorStore.getState().helpDependence, 3),
          misconceptions: [],
          concepts: useTutorStore.getState().concepts.map(c => c.id),
          problem_type: problemType,
          problem_text: problemText,
          mode,
        })
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Tutor request failed (${res.status}).`);
      }

      const data = await res.json();
      if (typeof data.message !== "string" || !data.message.trim()) {
        throw new Error("The tutor returned an empty reply. Your message is still here—please try again.");
      }
      
      addMessage({ role: 'tutor', content: data.message, hintLevel: data.hint_level });
      if (data.response_type === "hint") incrementHelpDependence();
      if (data.session_completed) {
        setRewardPoints(data.reward_points);
        completeSession(data.independent_solve ? "verified" : data.verified ? "assisted" : "learning_goal");
      }

      if (data.concept_updates && data.concept_updates.length > 0) {
        for (const update of data.concept_updates) {
          const conceptId = update.concept.toLowerCase().replace(/\s+/g, "_");
          updateConcept(conceptId, update.status, update.status === "needs_practice" ? 0 : 0.5);
          if (update.status === "needs_practice") {
            addMisconception(conceptId, update.evidence || "Misconception detected.");
          }
        }
      }
    } catch (err) {
      console.error(err);
      setInputValue(submittedInput);
      setSendError(err instanceof Error ? err.message : "Unable to reach the tutor. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  if (isLoadingSession) {
    return <div className="grid min-h-[70vh] place-items-center p-6"><EmptyState title="Picking up where you left off…" description="Your session is loading. Your next idea is just a moment away." illustration="book" /></div>;
  }

  if (sessionError) {
    return (
      <div className="page-shell grid min-h-[70vh] max-w-xl place-content-center py-12 text-center">
        <h1 className="text-2xl font-semibold">Unable to open this session</h1>
        <p role="alert" className="mt-2 text-sm text-destructive">{sessionError}</p>
        <Link className="theme-button mt-6 inline-flex min-h-11 items-center justify-center bg-primary px-4 font-bold text-primary-foreground" to="/learn">Start a new session</Link>
      </div>
    );
  }

  if (isCompleted) {
    return (
      <div className="h-[100dvh] overflow-y-auto bg-bg">
        <SummaryView />
      </div>
    );
  }

  if (!problemText) {
    return (
      <div className="page-shell grid min-h-[70vh] max-w-xl place-content-center py-12 text-center">
        <h1 className="text-2xl font-semibold">This session is no longer available</h1>
        <p className="mt-2 text-muted-foreground">
          This session could not be restored. Start a new session to continue learning.
        </p>
        <Link className="theme-button mt-6 inline-flex min-h-11 items-center justify-center bg-primary px-4 font-bold text-primary-foreground" to="/learn">Start a new session</Link>
      </div>
    );
  }

  const userSteps = messages.filter(message => message.role === "user").length;
  const avgHints = userSteps > 0 ? helpDependence / userSteps : 0;
  const independence = Math.round(Math.max(0, Math.min(100, (1 - avgHints) * 100)));
  const mobileTabs = [
    { id: "problem" as const, label: "Problem", Icon: BookOpen },
    { id: "tutor" as const, label: "Tutor", Icon: MessageCircle },
    { id: "map" as const, label: "Map", Icon: Map },
    { id: "progress" as const, label: "Progress", Icon: Target },
  ];

  return (
    <main className="flex h-[100dvh] flex-col overflow-hidden bg-bg">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b-2 border-ink bg-surface px-3 py-2 sm:px-5">
        <Link to="/dashboard" aria-label="Back to learning history" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border-2 border-ink bg-yellow">
          <BookOpen aria-hidden="true" className="h-5 w-5" />
        </Link>
        <div className="min-w-0 flex-1 text-center sm:text-left">
          <p className="truncate font-display text-sm font-extrabold sm:text-base">Study space</p>
          <p className="hidden text-xs text-muted-foreground sm:block">Your ideas, one step at a time</p>
        </div>
        <Link
          to="/learn"
          className="inline-flex min-h-10 shrink-0 items-center gap-1.5 rounded-xl border-2 border-ink bg-primary px-2 text-xs font-bold text-primary-foreground shadow-[var(--shadow-hard)] sm:gap-2 sm:px-3 sm:text-sm"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          <span className="hidden min-[380px]:inline">New problem</span>
          <span className="min-[380px]:hidden">New</span>
        </Link>
        <ModeSelector />
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(220px,0.78fr)_minmax(400px,1.4fr)_minmax(260px,0.9fr)]">
        <aside className={`${mobileTab === "problem" ? "flex" : "hidden"} min-h-0 flex-col gap-4 overflow-y-auto p-4 pb-24 soft-scrollbar lg:flex lg:border-r-2 lg:border-ink lg:bg-yellow/30`}>
          <details open className="theme-card sticky top-0 z-10 bg-yellow p-4">
            <summary className="cursor-pointer font-display text-lg font-extrabold">Your problem</summary>
            <div className="prose prose-sm max-w-none break-words text-ink">
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{problemText}</ReactMarkdown>
            </div>
          </details>
          <ThemeCard variant="white" className="p-4">
            <div className="mb-3 flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-full border-2 border-ink bg-sky">
                <Sparkles aria-hidden="true" className="h-4 w-4" />
              </span>
              <h3 className="font-display font-extrabold">Your steps</h3>
            </div>
            <StepLadder />
          </ThemeCard>
          <div className="hidden lg:block">
            <HintMeter />
          </div>
        </aside>

        <section className={`${mobileTab === "tutor" ? "flex" : "hidden"} min-h-0 min-w-0 flex-col lg:flex lg:border-r-2 lg:border-ink`}>
          <div className="flex shrink-0 items-center justify-between border-b-2 border-ink bg-lilac/50 px-4 py-2">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Guided conversation</span>
            <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-mint ring-2 ring-ink" /> A safe space to try
            </span>
          </div>
          <div className="flex-1 space-y-4 overflow-y-auto px-3 py-4 pb-4 soft-scrollbar sm:px-6 lg:px-8">
            {sendError && <p role="alert" className="rounded-xl border-2 border-ink bg-coral p-3 text-sm font-semibold">{sendError}</p>}
            {messages.map(msg => (
              <motion.div
                key={msg.id}
                initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 260, damping: 24 }}
                className={`flex items-end gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "tutor" && (
                  <span className="mb-1 grid h-8 w-8 shrink-0 place-items-center rounded-full border-2 border-ink bg-yellow">
                    <Lightbulb aria-hidden="true" className="h-4 w-4" />
                  </span>
                )}
                <div
                  aria-live={msg.role === "tutor" ? "polite" : undefined}
                  className={`max-w-[min(88%,65ch)] rounded-2xl border-2 border-ink px-4 py-3 ${
                    msg.role === "user"
                      ? "rounded-br-sm bg-sky text-ink shadow-[var(--shadow-hard)]"
                      : "chat-reading-surface rounded-bl-sm text-ink shadow-[var(--shadow-hard)]"
                  }`}
                >
                  {msg.role === "tutor" && (
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="text-xs font-extrabold">Your tutor</span>
                      <span className="rounded-full border border-ink bg-lilac px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
                        {msg.hintLevel && msg.hintLevel > 0 ? "Hint" : "Question"}
                      </span>
                    </div>
                  )}
                  {msg.role === "tutor" ? (
                    <div className="prose prose-sm max-w-none break-words text-ink">
                      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                  )}
                  {msg.role === "tutor" && msg.hintLevel !== undefined && msg.hintLevel > 0 && (
                    <p className="mt-2 text-xs font-bold text-muted-foreground">Hint level {msg.hintLevel} of 3</p>
                  )}
                </div>
                {msg.role === "user" && (
                  <span className="mb-1 grid h-8 w-8 shrink-0 place-items-center rounded-full border-2 border-ink bg-mint text-xs font-extrabold">You</span>
                )}
              </motion.div>
            ))}
            {isSending && (
              <div className="flex items-center gap-2" role="status" aria-live="polite">
                <span className="grid h-8 w-8 place-items-center rounded-full border-2 border-ink bg-yellow"><Lightbulb aria-hidden="true" className="h-4 w-4" /></span>
                <span className="rounded-full border-2 border-ink bg-surface px-4 py-2 text-sm text-muted-foreground">Thinking about your next step…</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <footer className="shrink-0 border-t-2 border-ink bg-surface px-3 pb-[calc(env(safe-area-inset-bottom)+5rem)] pt-3 sm:px-5 lg:pb-4">
            {problemType === "code" ? (
              <Suspense fallback={<p className="text-sm text-muted-foreground">Loading code editor…</p>}>
                <p className="mb-2 text-xs text-muted-foreground">Code is sent to the tutor as text; it is not executed here.</p>
                <CodeEditor value={inputValue} onChange={setInputValue} onSubmit={() => void handleSubmit()} />
              </Suspense>
            ) : problemType === "closed_form" ? (
              <MathInput value={inputValue} onChange={setInputValue} onSubmit={() => void handleSubmit()} disabled={isCompleted} />
            ) : (
              <form onSubmit={event => { event.preventDefault(); void handleSubmit(); }} className="mx-auto flex w-full max-w-[65ch] gap-2">
                <textarea
                  value={inputValue}
                  onChange={event => setInputValue(event.target.value)}
                  onInput={event => {
                    event.currentTarget.style.height = "auto";
                    event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 128)}px`;
                  }}
                  onKeyDown={event => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void handleSubmit();
                    }
                  }}
                  rows={1}
                  aria-label="Your response to the tutor"
                  placeholder="Share your next thought…"
                  className="theme-input min-h-12 max-h-32 min-w-0 flex-1 resize-y px-4 py-3 text-sm placeholder:text-muted-foreground"
                  disabled={isCompleted}
                />
                <ThemeButton type="submit" className="min-h-12 w-12 shrink-0 px-0" aria-label="Send your response" disabled={isCompleted || !inputValue.trim()}>
                  <Send aria-hidden="true" className="h-5 w-5" />
                </ThemeButton>
              </form>
            )}
            <p className="mx-auto mt-2 hidden max-w-[65ch] text-[11px] text-muted-foreground sm:block">Enter to send · Shift + Enter for a new line</p>
          </footer>
        </section>

        <aside className={`${mobileTab === "map" ? "flex" : "hidden"} min-h-0 flex-col overflow-hidden p-4 pb-24 lg:flex lg:bg-lilac/20`}>
          <div className="mb-3 flex shrink-0 items-center justify-between">
            <span>
              <span className="block font-display text-xl font-extrabold">Learning map</span>
              <span className="text-xs text-muted-foreground">Prerequisites flow toward the key idea</span>
            </span>
            <span className="grid h-9 w-9 place-items-center rounded-full border-2 border-ink bg-lilac"><Map aria-hidden="true" className="h-4 w-4" /></span>
          </div>
          {learningObjective && (
            <p className="mb-3 shrink-0 rounded-xl border-2 border-ink bg-surface px-3 py-2 text-xs leading-relaxed text-muted-foreground">
              <span className="font-bold text-ink">Learning goal: </span>{learningObjective}
            </p>
          )}
          <ThemeCard variant="white" className="flex min-h-0 flex-1 flex-col overflow-hidden p-1">
            <Suspense fallback={<p className="p-4 text-sm text-muted-foreground">Loading your concept map…</p>}>
              <ConceptMap />
            </Suspense>
          </ThemeCard>
        </aside>

        <section className={`${mobileTab === "progress" ? "flex" : "hidden"} min-h-0 flex-col gap-4 overflow-y-auto p-4 pb-24 lg:hidden`}>
          <div>
            <span className="sticker-chip inline-flex rotate-1 bg-mint">YOUR MOMENTUM</span>
            <h2 className="mt-3 font-display text-2xl font-extrabold">Progress, not perfection.</h2>
          </div>
          <ThemeCard variant="lilac" className="flex items-center gap-5 p-5">
            <IndependenceRing score={independence} />
            <div><h3 className="font-extrabold">Independence indicator</h3><p className="mt-1 text-xs text-ink/80">Based on the hints you&apos;ve used in this session.</p></div>
          </ThemeCard>
          <StatChip label="hints used" value={helpDependence} Icon={Lightbulb} />
          <ThemeCard variant="white" className="p-4">
            <h3 className="mb-3 font-display font-extrabold">Concepts in play</h3>
            {concepts.length ? (
              <ul className="space-y-3">{concepts.map(concept => <li key={concept.id} className="flex items-center justify-between gap-3"><span className="text-sm font-semibold">{concept.name}</span><StatusPill status={concept.status} /></li>)}</ul>
            ) : <p className="text-sm text-muted-foreground">No question-specific concepts were saved for this session.</p>}
          </ThemeCard>
        </section>
      </div>

      <nav aria-label="Session sections" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t-2 border-ink bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden">
        {mobileTabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setMobileTab(id)}
            aria-current={mobileTab === id ? "page" : undefined}
            className={`flex min-h-14 flex-col items-center justify-center gap-0.5 text-[10px] font-bold ${mobileTab === id ? "bg-yellow text-ink" : "bg-surface text-muted-foreground"}`}
          >
            <Icon aria-hidden="true" className="h-5 w-5" />
            {label}
          </button>
        ))}
      </nav>
    </main>
  );
}
