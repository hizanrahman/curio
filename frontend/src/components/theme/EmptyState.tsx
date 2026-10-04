import type { ReactNode } from "react";
import { ThemeCard } from "./ThemeCard";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
  illustration?: "spark" | "book" | "upload";
}

const illustrations: Record<NonNullable<EmptyStateProps["illustration"]>, ReactNode> = {
  spark: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" /></>,
  book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5v-16Z" /><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20M8 7h7M8 10h5" /></>,
  upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" /></>,
};

export function EmptyState({ title, description, action, illustration = "spark" }: EmptyStateProps) {
  return (
    <ThemeCard variant="lilac" className="mx-auto max-w-lg p-6 text-center sm:p-8">
      <svg className="mx-auto mb-4 h-14 w-14 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {illustrations[illustration]}
      </svg>
      <h2 className="text-2xl font-extrabold">{title}</h2>
      <p className="mx-auto mt-2 max-w-sm text-sm text-ink/80">{description}</p>
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </ThemeCard>
  );
}
