import { useTutorStore } from "@/store/useTutorStore";
import { AlertCircle } from "lucide-react";

export function MisconceptionList() {
  const misconceptions = useTutorStore(state => state.misconceptions);
  const concepts = useTutorStore(state => state.concepts);
  
  if (misconceptions.length === 0) return null;

  const conceptNames = [...new Set(misconceptions.map(misconception => {
    const concept = concepts.find(item => item.id === misconception.conceptId);
    return concept?.name ?? "a learning topic";
  }))];
  const message = conceptNames.length === 1
    ? `We can revisit ${conceptNames[0]} together.`
    : "We can revisit a couple of learning topics together.";

  return (
    <div role="status" className="flex items-start gap-2 rounded-xl border-2 border-ink bg-yellow/70 p-3 text-xs text-ink">
      <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
      <p><span className="font-bold">Worth another look:</span> {message}</p>
    </div>
  );
}
