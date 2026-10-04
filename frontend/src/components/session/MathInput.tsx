import { Send } from "lucide-react";
import { ThemeButton } from "@/components/theme/ThemeButton";

export function MathInput({ value, onChange, onSubmit, disabled }: { value: string, onChange: (v: string) => void, onSubmit: () => void, disabled: boolean }) {
  const insertSymbol = (sym: string) => {
    onChange(value + sym);
  };

  const symbols = ['+', '-', '×', '÷', '=', 'x', 'y', '^2', '√', 'π'];

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="flex gap-1 flex-wrap">
        {symbols.map(s => (
          <button 
            key={s} 
            type="button"
            onClick={() => insertSymbol(s)}
            className="min-h-9 rounded-lg border-2 border-ink bg-secondary px-3 py-1 text-xs font-mono font-bold hover:bg-yellow"
          >
            {s}
          </button>
        ))}
      </div>
      <form 
        onSubmit={(e) => { e.preventDefault(); onSubmit(); }} 
        className="mx-auto flex w-full max-w-[65ch] gap-2"
      >
        <input 
          type="text" 
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter mathematical response..." 
          className="theme-input min-h-12 w-full px-4 py-3 font-mono text-sm placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled}
        />
        <ThemeButton 
          type="submit" 
          aria-label="Send your response"
          disabled={disabled || !value.trim()}
          className="min-h-12 w-12 shrink-0 px-0"
        >
          <Send aria-hidden="true" className="h-4 w-4" />
        </ThemeButton>
      </form>
    </div>
  );
}
