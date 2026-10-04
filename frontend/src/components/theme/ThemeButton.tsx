import type { ButtonHTMLAttributes } from "react";

type ThemeButtonVariant = "primary" | "secondary" | "ghost";

interface ThemeButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ThemeButtonVariant;
}

const variantClasses: Record<ThemeButtonVariant, string> = {
  primary: "bg-primary text-primary-foreground",
  secondary: "bg-surface text-foreground",
  ghost: "bg-surface text-foreground hover:bg-secondary",
};

export function ThemeButton({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ThemeButtonProps) {
  return (
    <button
      type={type}
      className={`theme-button inline-flex min-h-11 items-center justify-center gap-2 px-5 py-2.5 text-sm font-bold disabled:pointer-events-none disabled:opacity-50 ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}
