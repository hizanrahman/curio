import type { LucideIcon } from "lucide-react";

interface StatChipProps {
  label: string;
  value: string | number;
  Icon?: LucideIcon;
}

export function StatChip({ label, value, Icon }: StatChipProps) {
  return (
    <div className="inline-flex min-h-12 items-center gap-3 rounded-full border-2 border-ink bg-surface px-4 py-2">
      {Icon && <Icon aria-hidden="true" className="h-4 w-4 text-primary" />}
      <span className="font-mono text-sm font-bold">{value}</span>
      <span className="text-xs font-semibold text-muted-foreground">{label}</span>
    </div>
  );
}
