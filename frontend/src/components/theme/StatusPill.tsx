import { AlertCircle, CheckCircle2, Circle } from "lucide-react";
import type { ConceptStatus } from "@/store/useTutorStore";

const statusContent: Record<ConceptStatus, { label: string; classes: string; Icon?: typeof Circle }> = {
  mastered: { label: "Mastered", classes: "bg-mint text-ink", Icon: CheckCircle2 },
  developing: { label: "Developing", classes: "bg-yellow text-ink" },
  needs_practice: { label: "Needs practice", classes: "bg-coral text-ink", Icon: AlertCircle },
  not_assessed: { label: "Not assessed", classes: "bg-surface text-status-neutral", Icon: Circle },
};

export function ConceptStatusIcon({ status, className = "" }: { status: ConceptStatus; className?: string }) {
  if (status === "developing") {
    return (
      <svg aria-hidden="true" className={className} viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="6.25" stroke="currentColor" strokeWidth="1.8" />
        <path d="M8 1.75a6.25 6.25 0 0 0 0 12.5V1.75Z" fill="currentColor" />
      </svg>
    );
  }
  const Icon = statusContent[status].Icon ?? Circle;
  const iconColor = status === "not_assessed" ? "text-status-neutral" : "";
  return <Icon aria-hidden="true" className={`${className} ${iconColor}`} strokeWidth={2.5} />;
}

export function StatusPill({ status }: { status: ConceptStatus }) {
  const { label, classes } = statusContent[status];
  return (
    <span className={`inline-flex w-fit items-center gap-1.5 rounded-full border-2 border-ink px-2.5 py-1 text-xs font-bold ${classes}`}>
      <ConceptStatusIcon status={status} className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}
