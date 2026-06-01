import { Target, GitCompareArrows, Bug, Activity } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { CountUp } from '@/components/CountUp';

/**
 * "Measured, not vibes" — credibility panel with HONEST numbers only.
 * - UNFAIR-ToS (LexGLUE) benchmark: 84% recall @ 4.3% FPR (95% CIs)
 * - Cross-family agreement vs Gemini 2.5 Flash: severity kappa +0.419, category +0.531
 * - The harness even caught its own measurement bugs and corrected them.
 * Styled as a terminal "report" panel — no invented figures.
 */

export function EvalReport() {
  return (
    <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
      <Reveal as="div" className="max-w-2xl">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
          Measured, not vibes
        </span>
        <h2 className="mt-3 font-display font-bold text-2xl lg:text-4xl tracking-tight leading-[1.1]">
          Graded against a public benchmark.
        </h2>
        <p className="mt-4 text-sm lg:text-base text-muted-foreground leading-relaxed">
          A detector is only as good as its evals. This one is scored on the public{' '}
          <span className="text-foreground">UNFAIR-ToS</span> dataset (LexGLUE) and cross-checked
          against an independent model — with confidence intervals, not adjectives.
        </p>
      </Reveal>

      {/* report panel — terminal aesthetic */}
      <Reveal
        as="div"
        variant="scale"
        delay={80}
        className="relative mt-10 overflow-hidden rounded-2xl border border-white/[0.06] bg-card/30 backdrop-blur-xl shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset,0_30px_80px_-40px_rgba(0,0,0,0.9)]"
      >
        <span className="pointer-events-none absolute inset-x-12 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

        {/* report header bar */}
        <div className="flex items-center justify-between border-b border-border/40 bg-background/40 px-5 py-3">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_hsl(160_84%_39%/0.7)]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              eval_report.txt
            </span>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground/60">
            reproducible · CI-gated
          </span>
        </div>

        <div className="grid gap-px bg-border/30 md:grid-cols-2">
          {/* Benchmark recall / FPR */}
          <div className="bg-card/50 p-6 lg:p-8">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Target className="h-4 w-4 text-primary" />
              <span className="font-mono text-[10px] uppercase tracking-[0.16em]">
                UNFAIR-ToS · LexGLUE
              </span>
            </div>
            <div className="mt-5 flex items-end gap-8">
              <div>
                <CountUp
                  to={84}
                  suffix="%"
                  className="font-data text-4xl lg:text-5xl font-semibold text-emerald-500 leading-none"
                />
                <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                  recall
                </div>
              </div>
              <div>
                <CountUp
                  to={4.3}
                  decimals={1}
                  suffix="%"
                  className="font-data text-4xl lg:text-5xl font-semibold text-foreground leading-none"
                />
                <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                  false-positive rate
                </div>
              </div>
            </div>
            <p className="mt-5 text-[13px] text-muted-foreground leading-relaxed">
              Catches 84% of unfair clauses while wrongly flagging only 4.3% of fair ones — both
              reported with 95% confidence intervals.
            </p>
          </div>

          {/* Cross-family agreement */}
          <div className="bg-card/50 p-6 lg:p-8">
            <div className="flex items-center gap-2 text-muted-foreground">
              <GitCompareArrows className="h-4 w-4 text-primary" />
              <span className="font-mono text-[10px] uppercase tracking-[0.16em]">
                vs Gemini 2.5 Flash
              </span>
            </div>
            <div className="mt-5 flex items-end gap-8">
              <div>
                <CountUp
                  to={0.419}
                  decimals={3}
                  prefix="+"
                  className="font-data text-4xl lg:text-5xl font-semibold text-primary leading-none"
                />
                <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                  severity κ
                </div>
              </div>
              <div>
                <CountUp
                  to={0.531}
                  decimals={3}
                  prefix="+"
                  className="font-data text-4xl lg:text-5xl font-semibold text-primary leading-none"
                />
                <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                  category κ
                </div>
              </div>
            </div>
            <p className="mt-5 text-[13px] text-muted-foreground leading-relaxed">
              An independent model from a different family agrees on what’s risky and how risky —
              Cohen’s κ measures agreement beyond chance.
            </p>
          </div>
        </div>

        {/* self-correcting harness note */}
        <div className="flex items-start gap-3 border-t border-border/40 bg-background/40 px-5 py-4 lg:px-8">
          <span className="mt-0.5 inline-grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-amber-500/10 text-amber-500 ring-1 ring-amber-500/20">
            <Bug className="h-3.5 w-3.5" />
          </span>
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            <span className="text-foreground">The harness audits itself.</span> It caught its own
            measurement bugs — a kappa base-rate paradox and weak ground-truth labels — and corrected
            them, so the numbers above mean what they say.
          </p>
        </div>
      </Reveal>

      <p className="mt-4 flex items-center gap-2 font-mono text-[11px] text-muted-foreground/70">
        <Activity className="h-3.5 w-3.5 text-primary/70" />
        Gold holdout is sealed behind an import firewall and a CI regression gate.
      </p>
    </section>
  );
}
