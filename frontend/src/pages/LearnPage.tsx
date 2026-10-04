import { useEffect, useRef, useState } from "react";
import { ArrowRight, ClipboardPaste, FileImage, ImagePlus, Sparkles, UploadCloud } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTutorStore, type Concept } from "@/store/useTutorStore";
import { API_BASE_URL, authorizedFetch } from "@/lib/api";
import { ThemeButton } from "@/components/theme/ThemeButton";
import { ThemeCard } from "@/components/theme/ThemeCard";
import { APP_NAME, APP_TAGLINE } from "@/config";
import { PersonalityPrompt, type TutorPersonality } from "@/components/account/PersonalityPicker";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

interface ExtractedProblem {
  extracted_text: string;
}

export function LearnPage() {
  const [problemInput, setProblemInput] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [wasExtracted, setWasExtracted] = useState(false);
  const [showPersonalityPrompt, setShowPersonalityPrompt] = useState(
    () => typeof window !== "undefined" && window.localStorage.getItem(`${APP_NAME.toLowerCase()}-personality-prompt-dismissed`) !== "1",
  );
  const [personality, setPersonality] = useState<TutorPersonality>("chill_senior");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const setSession = useTutorStore(state => state.setSession);

  useEffect(() => {
    let active = true;
    void authorizedFetch(`${API_BASE_URL}/api/account/profile`)
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (active && data?.tutor_personality) setPersonality(data.tutor_personality as TutorPersonality);
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  const choosePersonality = async (value: TutorPersonality) => {
    setPersonality(value);
    try {
      const response = await authorizedFetch(`${API_BASE_URL}/api/account/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tutor_personality: value }),
      });
      if (!response.ok) throw new Error("Could not save the tutor personality.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save the tutor personality.");
    }
  };

  const dismissPersonalityPrompt = () => {
    window.localStorage.setItem(`${APP_NAME.toLowerCase()}-personality-prompt-dismissed`, "1");
    setShowPersonalityPrompt(false);
  };

  const handleExtractFile = async () => {
    if (!selectedFile) return;
    setIsBusy(true);
    setErrorMessage("");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await authorizedFetch(`${API_BASE_URL}/api/problems/extract`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `Text extraction failed (${response.status}).`);
      }

      const result: ExtractedProblem = await response.json();
      setProblemInput(result.extracted_text);
      setWasExtracted(true);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (cameraInputRef.current) cameraInputRef.current.value = "";
    } catch (err) {
      console.error(err);
      setErrorMessage(err instanceof Error ? err.message : "Unable to extract text from this file.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleStartSession = async () => {
    if (!problemInput.trim()) return;
    setIsBusy(true);
    setErrorMessage("");
    try {
      const response = await authorizedFetch(`${API_BASE_URL}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          problem_text: problemInput.trim(),
          mode: "explore",
          tutor_personality: personality,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `Session creation failed (${response.status}).`);
      }
      const data: {
        session_id: string;
        transfer_problem: string | null;
        learning_objective: string;
        concepts: Concept[];
        concept_links: { source: string; target: string }[];
      } = await response.json();
      setSession(
        data.session_id,
        problemInput.trim(),
        data.concepts,
        "explore",
        "conceptual",
        data.transfer_problem,
        data.concept_links,
        data.learning_objective,
      );
      navigate(`/session/${data.session_id}`);
    } catch (err) {
      console.error(err);
      setErrorMessage(err instanceof Error ? err.message : "Unable to start a tutoring session.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setErrorMessage("");
    if (file && file.size > 5 * 1024 * 1024) {
      setSelectedFile(null);
      event.target.value = "";
      setErrorMessage("The file is too large. Choose a file smaller than 5 MB.");
      return;
    }
    setSelectedFile(file);
    if (file) {
      setProblemInput("");
      setWasExtracted(false);
    }
  };

  return (
    <main className="page-shell max-w-5xl py-8 pb-16 sm:py-12">
      <div className="mb-8 space-y-5">
        {showPersonalityPrompt && (
          <PersonalityPrompt
            value={personality}
            onChange={value => void choosePersonality(value)}
            onDismiss={dismissPersonalityPrompt}
          />
        )}
      </div>
      <div className="grid items-start gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:gap-12">
        <div className="space-y-7">
          <div>
            <span className="sticker-chip inline-flex -rotate-2 items-center gap-2 bg-mint">
              <Sparkles aria-hidden="true" className="h-4 w-4" /> Your next “aha” starts here
            </span>
            <h1 className="mt-4 text-4xl font-extrabold tracking-tight sm:text-5xl">Bring a problem.<br /><span className="signature-highlight">{APP_TAGLINE}</span></h1>
            <p className="mt-4 max-w-xl text-muted-foreground">
            Ask any question or describe what you are studying. Your tutor will work with the wording you provide.
            </p>
          </div>

          <div
            onDragOver={event => { event.preventDefault(); setIsDragging(true); }}
            onDragLeave={event => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setIsDragging(false);
            }}
            onDrop={event => {
              event.preventDefault();
              setIsDragging(false);
              const file = event.dataTransfer.files?.[0] ?? null;
              if (file) {
                setErrorMessage("");
                if (file.size > 5 * 1024 * 1024) {
                  setSelectedFile(null);
                  setErrorMessage("The file is too large. Choose a file smaller than 5 MB.");
                  return;
                }
                setSelectedFile(file);
                setProblemInput("");
                setWasExtracted(false);
              }
            }}
            className={`rounded-2xl border-2 border-dashed border-ink p-5 sm:p-6 ${isDragging ? "bg-lilac" : "bg-surface"}`}
          >
            <div className="flex items-start gap-4">
              <span className="hidden h-12 w-12 shrink-0 place-items-center rounded-xl border-2 border-ink bg-sky sm:grid">
                <UploadCloud aria-hidden="true" className="h-6 w-6" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-lg font-extrabold">Drop in a worksheet or snap a photo</h2>
                <p className="mt-1 text-sm text-muted-foreground">PNG, JPEG, WebP, or PDF · up to 5 MB</p>
                <p className="mt-2 truncate text-sm font-semibold" aria-live="polite">{selectedFile?.name ?? "Images are used to extract text, not stored as uploads."}</p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <ThemeButton variant="secondary" onClick={() => fileInputRef.current?.click()}>
                <FileImage aria-hidden="true" className="h-4 w-4" /> Choose file
              </ThemeButton>
              <ThemeButton variant="secondary" className="md:hidden" onClick={() => cameraInputRef.current?.click()}>
                <ImagePlus aria-hidden="true" className="h-4 w-4" /> Take photo
              </ThemeButton>
              <ThemeButton
                variant="ghost"
                onClick={async () => {
                  try {
                    const text = await navigator.clipboard.readText();
                    if (text.trim()) {
                      setProblemInput(text);
                      setSelectedFile(null);
                      setWasExtracted(false);
                      setErrorMessage("");
                    } else {
                      setErrorMessage("There is no text on your clipboard yet.");
                    }
                  } catch {
                    setErrorMessage("Clipboard access is unavailable. You can paste directly into the text box.");
                  }
                }}
              >
                <ClipboardPaste aria-hidden="true" className="h-4 w-4" /> Paste text
              </ThemeButton>
            </div>
            <input
              ref={fileInputRef}
              className="sr-only"
              type="file"
              accept="image/png,image/jpeg,image/webp,application/pdf,.png,.jpg,.jpeg,.webp,.pdf"
              onChange={handleFileChange}
              disabled={isBusy}
              aria-label="Choose an image or PDF"
            />
            <input
              ref={cameraInputRef}
              className="sr-only"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileChange}
              disabled={isBusy}
              aria-label="Take or choose a problem photo"
            />
          </div>

          {selectedFile && (
            <ThemeCard variant="yellow" className="flex flex-col items-start justify-between gap-4 p-4 sm:flex-row sm:items-center">
              <div>
                <p className="font-bold">Ready to read: {selectedFile.name}</p>
                <p className="mt-1 text-xs text-ink/80">You&apos;ll review the extracted text before starting.</p>
              </div>
              <ThemeButton disabled={isBusy} onClick={() => void handleExtractFile()}>
                {isBusy ? "Reading your problem…" : "Read problem"} <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </ThemeButton>
            </ThemeCard>
          )}

          {isBusy && selectedFile && (
            <div className="space-y-2" role="status" aria-live="polite">
              <p className="text-sm font-bold">Reading your problem…</p>
              <div className="h-3 overflow-hidden rounded-full border-2 border-ink bg-surface">
                <div className="h-full w-2/3 animate-pulse bg-yellow" />
              </div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <ThemeCard variant="white" className="space-y-4 p-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <label htmlFor="problem-text" className="font-display text-xl font-extrabold">
                {wasExtracted ? "Check the extracted text" : "Or type your problem"}
              </label>
              <span className="sticker-chip inline-flex rotate-1 bg-lilac">Explore mode</span>
            </div>
            <textarea
              id="problem-text"
              className="theme-input min-h-48 w-full resize-y px-4 py-3 text-base leading-relaxed placeholder:text-muted-foreground focus-visible:outline-none"
              placeholder="Type or paste the question you’re working on…"
              value={problemInput}
              onChange={event => {
                setProblemInput(event.target.value);
                if (selectedFile) {
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }
                setWasExtracted(false);
              }}
              disabled={isBusy}
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">
                {wasExtracted ? "Extracted text · please review for OCR mistakes" : "Up to 8,000 characters"}
              </span>
              <ThemeButton
                disabled={isBusy || !problemInput.trim() || problemInput.length > 8000 || Boolean(selectedFile)}
                onClick={() => void handleStartSession()}
              >
                {isBusy ? "Starting session…" : "Looks right, start"} <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </ThemeButton>
            </div>
          </ThemeCard>

          {wasExtracted && problemInput.trim() && (
            <ThemeCard variant="sky" className="p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full border-2 border-ink bg-surface px-3 py-1 text-xs font-bold">Subject: not classified</span>
                <span className="rounded-full border-2 border-ink bg-surface px-3 py-1 text-xs font-bold">Type: not classified</span>
                <span className="rounded-full border-2 border-ink bg-yellow px-3 py-1 text-xs font-bold">Review extraction</span>
              </div>
              <div className="prose prose-sm max-w-none break-words text-ink">
                <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                  {problemInput}
                </ReactMarkdown>
              </div>
            </ThemeCard>
          )}

          {errorMessage && <p role="alert" className="rounded-xl border-2 border-ink bg-coral px-4 py-3 text-sm font-semibold">{errorMessage}</p>}
        </div>
      </div>
    </main>
  );
}
