import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { CheckCircle2, Lightbulb, Sparkles } from "lucide-react";
import { StatusPill } from "./StatusPill";
import { ThemeCard } from "./ThemeCard";

const demoTurns = [
  { student: "I think I should divide both sides by 3 first.", tutor: "Nice start. What would that leave on the left side?" },
  { student: "Then I would subtract 4 to get x alone.", tutor: "Exactly. How could you check that your value works?" },
  { student: "Plug it back into the original equation.", tutor: "You built a way to verify your own answer." },
];

export function DemoConversation() {
  const [turn, setTurn] = useState(0);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    if (shouldReduceMotion) return;
    const timer = window.setInterval(() => setTurn(current => (current + 1) % demoTurns.length), 8500);
    return () => window.clearInterval(timer);
  }, [shouldReduceMotion]);

  const activeTurn = demoTurns[turn];

  return (
    <ThemeCard variant="white" className="relative mx-auto w-full max-w-xl overflow-hidden p-4 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-full border-2 border-ink bg-lilac">
            <Sparkles aria-hidden="true" className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-extrabold">A little less answer-copying</p>
            <p className="text-xs text-muted-foreground">A tutor that helps you think</p>
          </div>
        </div>
        <span className="sticker-chip hidden rotate-2 sm:inline-flex">LIVE DEMO</span>
      </div>

      <div className="chat-reading-surface space-y-3 p-4">
        <div className="rounded-xl border-2 border-ink bg-yellow/60 px-3 py-2 text-sm font-bold">
          Try this: <span className="font-mono">3x + 12 = 24</span>
        </div>
        <motion.div key={`student-${turn}`} initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="ml-8 rounded-2xl rounded-tr-sm border-2 border-ink bg-sky p-3 text-sm font-medium">
          {activeTurn.student}
        </motion.div>
        <motion.div key={`tutor-${turn}`} initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mr-5 flex gap-2 rounded-2xl rounded-tl-sm border-2 border-ink bg-secondary p-3 text-sm">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border-2 border-ink bg-yellow">
            <Lightbulb aria-hidden="true" className="h-3.5 w-3.5" />
          </span>
          <span>{activeTurn.tutor}</span>
        </motion.div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 rounded-full border-2 border-ink bg-yellow px-3 py-1 text-xs font-bold">
          <CheckCircle2 aria-hidden="true" className="h-4 w-4" /> You checked your own work
        </span>
        <StatusPill status={turn === demoTurns.length - 1 ? "mastered" : "developing"} />
      </div>
    </ThemeCard>
  );
}
