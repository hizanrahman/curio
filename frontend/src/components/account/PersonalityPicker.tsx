import type { ReactNode } from "react";
import { Smile, Target, Telescope } from "lucide-react";

export type TutorPersonality = "chill_senior" | "strict_coach" | "curious_friend";

const personalities: {
  id: TutorPersonality;
  title: string;
  description: string;
  sample: string;
  Icon: typeof Smile;
}[] = [
  {
    id: "chill_senior",
    title: "Chill Senior",
    description: "Relaxed, encouraging, and naturally upbeat.",
    sample: "Nice start—let’s untangle the next step together.",
    Icon: Smile,
  },
  {
    id: "strict_coach",
    title: "Strict Coach",
    description: "Concise, focused, and kind about the effort.",
    sample: "Good. Show the operation you would use next.",
    Icon: Target,
  },
  {
    id: "curious_friend",
    title: "Curious Friend",
    description: "Enthusiastic and wondering alongside you.",
    sample: "Ooh, what changes if we compare those two parts?",
    Icon: Telescope,
  },
];

export function PersonalityPicker({
  value,
  onChange,
}: {
  value: TutorPersonality;
  onChange: (personality: TutorPersonality) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {personalities.map(({ id, title, description, sample, Icon }) => (
        <button
          key={id}
          type="button"
          onClick={() => onChange(id)}
          aria-pressed={value === id}
          className={`theme-card min-h-40 p-4 text-left transition-transform ${value === id ? "bg-yellow" : "bg-surface"} focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary`}
        >
          <span className="flex items-center gap-2 font-display font-extrabold"><Icon aria-hidden="true" className="h-4 w-4" />{title}</span>
          <span className="mt-2 block text-xs text-muted-foreground">{description}</span>
          <span className="mt-3 block rounded-lg border border-ink/30 bg-bg p-2 text-xs italic text-ink">“{sample}”</span>
        </button>
      ))}
    </div>
  );
}

export function PersonalityPrompt({
  value,
  onChange,
  onDismiss,
  children,
}: {
  value: TutorPersonality;
  onChange: (personality: TutorPersonality) => void;
  onDismiss: () => void;
  children?: ReactNode;
}) {
  return (
    <section className="space-y-4 rounded-2xl border-2 border-ink bg-lilac/50 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div><h2 className="font-display text-lg font-extrabold">Pick your tutor’s vibe</h2><p className="text-sm text-muted-foreground">Just the tone changes—your tutor still guides, never gives away answers.</p></div>
        {children}
      </div>
      <PersonalityPicker value={value} onChange={onChange} />
      <button type="button" onClick={onDismiss} className="min-h-10 rounded-lg px-3 text-sm font-bold underline underline-offset-4">Maybe later</button>
    </section>
  );
}
