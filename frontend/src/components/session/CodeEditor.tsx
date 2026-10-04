import Editor from "@monaco-editor/react";
import { ThemeButton } from "@/components/theme/ThemeButton";

export function CodeEditor({ value, onChange, onSubmit }: { value: string, onChange: (v: string) => void, onSubmit: () => void }) {
  return (
    <div className="flex h-[220px] w-full flex-col overflow-hidden rounded-xl border-2 border-ink bg-surface shadow-[var(--shadow-hard)]">
      <Editor
        height="100%"
        defaultLanguage="python"
        theme="vs-dark"
        value={value}
        onChange={(val) => onChange(val || "")}
        options={{
          minimap: { enabled: false },
          lineNumbers: "on",
          scrollBeyondLastLine: false,
        }}
      />
      <div className="flex justify-end border-t-2 border-ink bg-secondary p-2">
        <ThemeButton
          onClick={onSubmit}
          className="min-h-9 px-3 py-1 text-xs"
        >
          Send to tutor
        </ThemeButton>
      </div>
    </div>
  );
}
