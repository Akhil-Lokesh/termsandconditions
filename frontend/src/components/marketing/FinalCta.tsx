import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/Logo';
import { ArrowRight } from 'lucide-react';
import { Reveal } from '@/components/Reveal';

/**
 * Final CTA + footer. Glass panel with a cyan wash, primary/secondary CTAs to
 * /signup and /login, and the required disclaimer line. No fake copyright year.
 */

export function FinalCta() {
  return (
    <>
      <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20">
        <Reveal
          as="div"
          variant="scale"
          className="relative overflow-hidden rounded-3xl border border-white/[0.07] bg-card/30 px-6 py-14 text-center backdrop-blur-xl shadow-[0_1px_0_0_rgba(255,255,255,0.06)_inset,0_40px_120px_-50px_rgba(0,0,0,0.95)] lg:px-12 lg:py-20">
          {/* atmosphere */}
          <span className="pointer-events-none absolute inset-x-16 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          <span className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_80%_at_50%_0%,hsl(var(--primary)/0.12),transparent_70%)]" />
          <div className="noise-overlay pointer-events-none absolute inset-0" />

          <div className="relative">
            <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-muted/30 px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Free to try
              </span>
            </span>
            <h2 className="mx-auto mt-6 max-w-2xl font-display font-bold text-3xl lg:text-5xl tracking-tight leading-[1.05]">
              Know what you’re agreeing to.
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-sm lg:text-base text-muted-foreground leading-relaxed">
              Upload a Terms of Service or Privacy Policy and get the risky clauses, the missing
              protections, and a plain-English verdict — in seconds.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <Link to="/signup">
                <Button size="lg" className="glow-primary h-12 px-7 text-sm">
                  Analyze a document
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/login">
                <Button
                  size="lg"
                  variant="outline"
                  className="h-12 px-7 text-sm border-border-bright"
                >
                  Login
                </Button>
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      <footer className="relative z-10 border-t border-border/40">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-6 lg:px-8">
          <Logo showWordmark />
          <p className="text-center font-mono text-[11px] text-muted-foreground sm:text-right">
            Informational analysis, not legal advice. Built as an engineering portfolio project.
          </p>
        </div>
      </footer>
    </>
  );
}
