import { ListChecks, ShieldQuestion, SlidersHorizontal, ArrowRight, FileText } from 'lucide-react';
import { Reveal } from '@/components/Reveal';

/**
 * "How it works" — the 2-pass detection engine, made legible.
 * Document → (1) checklist match against curated patterns →
 * (2) missing-protection scan (relevance-gated) → (3) severity ranking → verdict.
 * Rendered as a terminal-style pipeline with glass stage cards and a connecting rail.
 */

const STAGES: {
  step: string;
  pass: string;
  icon: typeof ListChecks;
  title: string;
  body: string;
  meta: string;
}[] = [
  {
    step: '01',
    pass: 'Pass 1',
    icon: ListChecks,
    title: 'Checklist match',
    body: 'Every clause is tested against ~41 curated risk patterns — not an open-ended "find anything bad". Checklisting is what catches the severe clauses an open search skips.',
    meta: '~41 patterns',
  },
  {
    step: '02',
    pass: 'Pass 2',
    icon: ShieldQuestion,
    title: 'Missing-protection scan',
    body: 'Looks for the safeguards a fair agreement should include but doesn’t — breach notice, change notification, an account-termination appeal — gated for relevance so it never flags the irrelevant.',
    meta: 'relevance-gated',
  },
  {
    step: '03',
    pass: 'Rank',
    icon: SlidersHorizontal,
    title: 'Severity ranking',
    body: 'Findings are bucketed high / medium / low by consumer harm and ordered into a focused alert budget — the worst clauses surface first, noise stays out.',
    meta: '4 tiers',
  },
];

export function EngineDiagram() {
  return (
    <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
      <Reveal as="div" className="max-w-2xl">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
          How it works
        </span>
        <h2 className="mt-3 font-display font-bold text-2xl lg:text-4xl tracking-tight leading-[1.1]">
          A two-pass engine, not a black box.
        </h2>
        <p className="mt-4 text-sm lg:text-base text-muted-foreground leading-relaxed">
          Detection is deliberately simple and transparent: two focused LLM passes feeding a
          deterministic ranker. Each stage does one job you can reason about.
        </p>
      </Reveal>

      {/* glass pipeline container */}
      <div className="relative mt-10 overflow-hidden rounded-2xl border border-white/[0.06] bg-card/30 p-5 backdrop-blur-xl shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset,0_30px_80px_-40px_rgba(0,0,0,0.9)] lg:p-8">
        {/* top hairline sheen */}
        <span className="pointer-events-none absolute inset-x-12 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

        {/* source chip */}
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-muted/30 px-3 py-1.5">
            <FileText className="h-3.5 w-3.5 text-primary" />
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Terms of Service / Privacy Policy
            </span>
          </span>
          <span className="hidden h-px flex-1 bg-gradient-to-r from-border via-border/40 to-transparent sm:block" />
        </div>

        {/* stages */}
        <div className="relative mt-7 grid gap-4 lg:grid-cols-3 lg:gap-5">
          {/* connecting rail (desktop) — runs through the card centers so the
              arrow nodes sit on it; draws itself in on reveal */}
          <Reveal
            as="span"
            variant="rail"
            delay={120}
            className="pointer-events-none absolute left-0 right-0 top-1/2 hidden h-px bg-[linear-gradient(90deg,transparent,hsl(var(--primary)/0.35),hsl(var(--primary)/0.35),transparent)] lg:block"
          />

          {STAGES.map((s, i) => (
            <Reveal
              as="div"
              variant="up"
              delay={220 + i * 140}
              key={s.step}
              className="relative"
            >
              <div className="group relative h-full overflow-hidden rounded-xl border border-white/[0.06] bg-background/40 p-5 backdrop-blur-md transition-all duration-300 hover:border-primary/30 hover:bg-background/60">
                <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/12 to-transparent" />
                <div className="flex items-center justify-between">
                  <span className="inline-grid h-11 w-11 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20 transition-transform duration-300 group-hover:scale-105">
                    <s.icon className="h-5 w-5" />
                  </span>
                  <div className="text-right">
                    <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-primary/80">
                      {s.pass}
                    </div>
                    <div className="font-data text-lg font-semibold text-muted-foreground/40">
                      {s.step}
                    </div>
                  </div>
                </div>
                <h3 className="mt-4 font-display font-semibold text-base">{s.title}</h3>
                <p className="mt-2 text-[13px] text-muted-foreground leading-relaxed">{s.body}</p>
                <span className="mt-4 inline-flex items-center rounded-md border border-border/60 bg-muted/30 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {s.meta}
                </span>
              </div>

              {/* arrow between stages (desktop) */}
              {i < STAGES.length - 1 && (
                <span className="pointer-events-none absolute -right-3.5 top-1/2 z-10 hidden -translate-y-1/2 lg:grid">
                  <span className="grid h-7 w-7 place-items-center rounded-full border border-primary/30 bg-background/80 text-primary backdrop-blur">
                    <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </span>
              )}
            </Reveal>
          ))}
        </div>

        {/* verdict */}
        <div className="mt-7 flex items-center gap-3">
          <span className="hidden h-px flex-1 bg-gradient-to-l from-border via-border/40 to-transparent sm:block" />
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-primary">
              Ranked findings + missing protections
            </span>
          </span>
        </div>
      </div>
    </section>
  );
}
