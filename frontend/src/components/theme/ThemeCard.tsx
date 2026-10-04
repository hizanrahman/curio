import type { HTMLAttributes } from "react";

type ThemeCardVariant = "white" | "yellow" | "mint" | "lilac" | "sky" | "coral";

const variantClasses: Record<ThemeCardVariant, string> = {
  white: "bg-surface",
  yellow: "bg-yellow",
  mint: "bg-mint",
  lilac: "bg-lilac",
  sky: "bg-sky",
  coral: "bg-coral",
};

interface ThemeCardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: ThemeCardVariant;
  interactive?: boolean;
}

export function ThemeCard({
  variant = "white",
  interactive = false,
  className = "",
  ...props
}: ThemeCardProps) {
  return (
    <div
      className={`theme-card ${variantClasses[variant]} ${interactive ? "theme-card-interactive" : ""} ${className}`}
      {...props}
    />
  );
}
