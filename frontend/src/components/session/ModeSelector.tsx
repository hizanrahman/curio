import { useTutorStore, type TutorMode } from "@/store/useTutorStore";

export function ModeSelector() {
  const { mode, setMode } = useTutorStore();
  const modes: TutorMode[] = ['explore', 'homework', 'exam practice'];

  return (
    <div role="group" aria-label="Choose tutoring mode" className="flex max-w-[68vw] overflow-x-auto rounded-xl border-2 border-ink bg-secondary p-1 sm:max-w-none">
      {modes.map(m => (
        <button
          key={m}
          type="button"
          onClick={() => setMode(m)}
          aria-pressed={mode === m}
          className={`theme-button min-h-11 shrink-0 rounded-lg px-2.5 py-1 text-[11px] font-bold capitalize sm:px-3 sm:text-xs ${mode === m ? "bg-primary text-primary-foreground" : "bg-surface text-ink hover:bg-secondary"}`}
        >
          {m === "homework" ? "Homework" : m === "exam practice" ? "Exam" : "Explore"}
        </button>
      ))}
    </div>
  );
}
