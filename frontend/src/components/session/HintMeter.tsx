import { useTutorStore } from "@/store/useTutorStore";

export function HintMeter() {
  const helpDependence = useTutorStore(state => state.helpDependence);
  const level = Math.min(helpDependence, 3);

  return (
    <div className="rounded-2xl border-2 border-ink bg-surface p-4" title="A gentle reminder of how much help you have used. Every level is okay; the goal is understanding.">
      <div className="flex items-center justify-between gap-2 text-xs font-bold">
        <span>Hint meter</span>
        <span className="text-muted-foreground">{helpDependence} used</span>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-1.5" role="img" aria-label={`Hint level ${level} of 3`}>
        {Array.from({ length: 4 }, (_, index) => (
          <span
            key={index}
            className={`h-2.5 rounded-full border border-ink ${index <= level ? "bg-primary" : "bg-secondary"}`}
          />
        ))}
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">A hint is a tool, not a score. Ask for the nudge you need.</p>
    </div>
  );
}
