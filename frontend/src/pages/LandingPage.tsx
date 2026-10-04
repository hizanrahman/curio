import { lazy, Suspense } from "react";
import { ArrowRight, Brain, Check, ChevronRight, Compass, Lightbulb, Network, ShieldCheck, Sparkles, Target, Upload, WandSparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { ThemeCard } from "@/components/theme/ThemeCard";
import { APP_NAME, APP_TAGLINE } from "@/config";

const DemoConversation = lazy(() => import("@/components/theme/DemoConversation").then(module => ({ default: module.DemoConversation })));

const steps = [
  { number: "01", title: "Bring a problem", description: "Type it in or upload a worksheet, photo, or PDF.", Icon: Upload, variant: "yellow" as const },
  { number: "02", title: "Make your attempt", description: "Start with what you know. Half-formed ideas count.", Icon: Brain, variant: "mint" as const },
  { number: "03", title: "Get a nudge", description: "Follow a focused question or hint, one step at a time.", Icon: Lightbulb, variant: "lilac" as const },
  { number: "04", title: "Own the idea", description: "Build understanding you can use on the next problem.", Icon: Target, variant: "sky" as const },
];

const features = [
  { title: "Hints that meet you where you are", description: "Get a small nudge first, then a clearer hint when you need one.", Icon: Lightbulb, variant: "yellow" as const, className: "md:col-span-2" },
  { title: "See ideas connect", description: "A visual concept map helps connect today’s work to the bigger picture.", Icon: Network, variant: "lilac" as const, className: "" },
  { title: "Spot the step to revisit", description: "Notice a mismatch in reasoning and try another route without shame.", Icon: Compass, variant: "sky" as const, className: "" },
  { title: "Practice independence", description: "Celebrate progress from your own reasoning—not just fast answers.", Icon: ShieldCheck, variant: "mint" as const, className: "" },
  { title: "Works across subjects", description: "Bring the question you are studying, from algebra to history.", Icon: WandSparkles, variant: "yellow" as const, className: "md:col-span-2" },
];

export function LandingPage() {
  return (
    <main>
      <section className="page-shell grid min-h-[calc(100svh-64px)] items-center gap-10 py-12 lg:grid-cols-[1.05fr_0.95fr] lg:py-16 lg:gap-16">
        <div className="entrance-rise">
          <span className="sticker-chip mb-6 inline-flex -rotate-2 items-center gap-2 bg-mint">
            <Sparkles aria-hidden="true" className="h-4 w-4" /> A tutor for your next “wait, why?”
          </span>
          <h1 className="max-w-3xl text-[clamp(2.35rem,8vw,5.5rem)] font-extrabold leading-[0.98] tracking-[-0.055em]">
            Don&apos;t get the answer.
            <span className="mt-2 block"><span className="signature-highlight">Learn how to find it.</span></span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Bring a problem from class. Get thoughtful questions and useful hints that help you do the thinking—across the subjects you&apos;re learning.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/learn" className="theme-button inline-flex min-h-12 items-center justify-center gap-2 bg-primary px-6 font-bold text-primary-foreground">
              Start learning <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
            <a href="#how-it-works" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border-2 border-ink bg-surface px-6 text-sm font-bold">
              See how it works <ChevronRight aria-hidden="true" className="h-4 w-4" />
            </a>
          </div>
          <p className="mt-4 text-xs font-medium text-muted-foreground">No “just copy this” answers. Your reasoning stays yours.</p>
        </div>
        <div className="entrance-rise stagger-2">
          <Suspense fallback={<div className="mx-auto h-64 max-w-xl animate-pulse rounded-2xl border-2 border-ink bg-surface sm:h-72" aria-label="Loading conversation demo" />}>
            <DemoConversation />
          </Suspense>
          <div className="mx-auto mt-5 flex max-w-xl flex-wrap justify-center gap-2">
            {["Math", "Physics", "Chemistry", "Biology", "CS", "Humanities"].map(subject => (
              <span key={subject} className="sticker-chip -rotate-1 even:rotate-1">{subject}</span>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="border-y-2 border-ink bg-surface py-16 sm:py-20">
        <div className="page-shell">
          <div className="mx-auto max-w-2xl text-center">
            <span className="sticker-chip inline-flex -rotate-2 bg-sky">YOUR STUDY FLOW</span>
            <h2 className="mt-4 text-3xl font-extrabold sm:text-5xl">Four small steps. <span className="signature-highlight">One big shift.</span></h2>
            <p className="mt-4 text-muted-foreground">From “I’m stuck” to “I can explain why.”</p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map(({ number, title, description, Icon, variant }, index) => (
              <ThemeCard key={number} variant={variant} interactive className={`entrance-rise stagger-${index + 1} p-5`}>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-bold">{number}</span>
                  <Icon aria-hidden="true" className="h-6 w-6" />
                </div>
                <h3 className="mt-6 text-xl font-extrabold">{title}</h3>
                <p className="mt-2 text-sm text-ink/80">{description}</p>
              </ThemeCard>
            ))}
          </div>
        </div>
      </section>

      <section className="page-shell py-16 sm:py-20">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <span className="sticker-chip inline-flex rotate-1 bg-yellow">MADE FOR THE “WHY?”</span>
            <h2 className="mt-4 text-3xl font-extrabold sm:text-5xl">A study buddy, <span className="signature-highlight">not a shortcut.</span></h2>
          </div>
          <p className="max-w-md text-sm text-muted-foreground">Designed to make practice feel clearer, kinder, and more like your own work.</p>
        </div>
        <div className="mt-9 grid auto-rows-fr gap-5 md:grid-cols-3">
          {features.map(({ title, description, Icon, variant, className }, index) => (
            <ThemeCard key={title} variant={variant} interactive className={`entrance-rise stagger-${(index % 4) + 1} min-h-48 p-6 ${className}`}>
              <span className="grid h-11 w-11 place-items-center rounded-xl border-2 border-ink bg-surface">
                <Icon aria-hidden="true" className="h-5 w-5" />
              </span>
              <h3 className="mt-5 text-xl font-extrabold">{title}</h3>
              <p className="mt-2 max-w-sm text-sm text-ink/80">{description}</p>
              {title === "Works across subjects" && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {["Math", "Physics", "Chemistry", "Biology", "CS", "Humanities"].map(subject => (
                    <span key={subject} className="rounded-full border-2 border-ink bg-surface px-2.5 py-1 text-xs font-bold">{subject}</span>
                  ))}
                </div>
              )}
            </ThemeCard>
          ))}
        </div>
      </section>

      <section className="border-y-2 border-ink bg-lilac py-16 sm:py-20">
        <div className="page-shell">
          <div className="mx-auto max-w-2xl text-center">
            <span className="sticker-chip inline-flex -rotate-2 bg-surface">THE DIFFERENCE</span>
            <h2 className="mt-4 text-3xl font-extrabold sm:text-5xl">Not another answer machine.</h2>
          </div>
          <div className="mx-auto mt-9 grid max-w-4xl gap-5 md:grid-cols-2">
            <ThemeCard variant="white" className="p-6 sm:p-8">
              <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Typical AI</p>
              <p className="mt-4 text-2xl font-extrabold">“Here&apos;s the answer.”</p>
              <p className="mt-3 text-sm text-muted-foreground">Fast to copy. Easy to forget. You might not know how it works.</p>
              <span className="mt-6 inline-flex items-center gap-2 rounded-full bg-secondary px-3 py-1 text-xs font-bold"><span aria-hidden="true">—</span> Answer first</span>
            </ThemeCard>
            <ThemeCard variant="yellow" className="p-6 sm:p-8">
              <p className="text-xs font-bold uppercase tracking-widest">{APP_NAME}</p>
              <p className="mt-4 text-2xl font-extrabold">“What would you try?”</p>
              <p className="mt-3 text-sm text-ink/80">A question, a useful nudge, and room to build the answer yourself.</p>
              <span className="mt-6 inline-flex items-center gap-2 rounded-full border-2 border-ink bg-surface px-3 py-1 text-xs font-bold"><Check aria-hidden="true" className="h-4 w-4" /> Your thinking first</span>
            </ThemeCard>
          </div>
        </div>
      </section>

      <section className="page-shell py-16 sm:py-20">
        <ThemeCard variant="mint" className="flex flex-col items-start justify-between gap-6 p-7 sm:flex-row sm:items-center sm:p-10">
          <div>
            <p className="font-mono text-xs font-bold uppercase tracking-widest">Your turn</p>
            <h2 className="mt-2 text-3xl font-extrabold sm:text-4xl">Bring the problem you&apos;re stuck on.</h2>
            <p className="mt-3 text-sm text-ink/80">Start with one question. See where your thinking takes you.</p>
          </div>
          <Link to="/learn" className="theme-button inline-flex min-h-12 shrink-0 items-center gap-2 bg-primary px-6 font-bold text-primary-foreground">
            Start learning <ArrowRight aria-hidden="true" className="h-4 w-4" />
          </Link>
        </ThemeCard>
      </section>

      <footer className="border-t-2 border-ink bg-surface py-8">
        <div className="page-shell flex flex-col gap-5 text-sm sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-display font-extrabold">{APP_NAME}</p>
            <p className="text-xs text-muted-foreground">{APP_TAGLINE}</p>
            <p className="mt-1 text-xs text-muted-foreground">Think it through. Make it yours.</p>
          </div>
          <div className="grid gap-2 text-xs text-muted-foreground sm:max-w-xl sm:grid-cols-3">
            <p><span className="font-bold text-ink">Privacy:</span> Uploaded images and PDFs are used to extract text and are not stored as uploads.</p>
            <p><span className="font-bold text-ink">Terms:</span> Use this as a learning aid; check your school&apos;s guidance for classwork.</p>
            <p><span className="font-bold text-ink">Contact:</span> Ask your school or account administrator for product support.</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
