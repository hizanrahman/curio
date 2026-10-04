import { Footprints } from "lucide-react";
import { useTutorStore } from "@/store/useTutorStore";
import { StatusPill } from "@/components/theme/StatusPill";

export function StepLadder() {
  const concepts = useTutorStore(state => state.concepts);

  if (concepts.length === 0) {
    return <p className="text-sm text-muted-foreground">Learning topics will appear here when available.</p>;
  }

  return (
    <div>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Footprints aria-hidden="true" className="h-4 w-4 text-primary" /> Your steps</h3>
      <ol className="space-y-2 text-sm text-ink">
        {concepts.map((concept, index) => (
          <li key={concept.id} className="flex items-start gap-2 rounded-xl bg-secondary px-3 py-2">
            <span className="pt-0.5 font-mono text-xs font-bold text-muted-foreground">{String(index + 1).padStart(2, "0")}</span>
            <span className="min-w-0 flex-1 font-semibold">{concept.name}</span>
            <StatusPill status={concept.status} />
          </li>
        ))}
      </ol>
    </div>
  );
}
