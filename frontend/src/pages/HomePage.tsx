import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Logo, LogoMark } from '@/components/Logo';
import { ArrowRight, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { ScrollProgress } from '@/components/ScrollProgress';
import { RiskCatalog } from '@/components/marketing/RiskCatalog';
import { EngineDiagram } from '@/components/marketing/EngineDiagram';
import { EvalReport } from '@/components/marketing/EvalReport';
import { SampleFindings } from '@/components/marketing/SampleFindings';
import { Faq } from '@/components/marketing/Faq';
import { FinalCta } from '@/components/marketing/FinalCta';

const NAV_LINKS = [
  { href: '#catches', label: 'What it catches' },
  { href: '#engine', label: 'How it works' },
  { href: '#evals', label: 'Benchmarks' },
];

const STATS = [
  { value: '~41', label: 'curated risk patterns' },
  { value: '84%', label: 'recall on UNFAIR-ToS' },
  { value: '+0.42', label: 'cross-model severity κ' },
  { value: '2-pass', label: 'LLM engine + ranker' },
];

export default function HomePage() {
  const rootRef = useRef<HTMLDivElement>(null);

  // Subtle scroll parallax on the atmosphere layers. Writes a CSS var straight
  // to the DOM (no React state) so scrolling never re-renders the page tree.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;

    let frame = 0;
    const update = () => {
      frame = 0;
      root.style.setProperty('--sy', String(window.scrollY));
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={rootRef} className="relative min-h-screen overflow-hidden">
      <ScrollProgress />

      {/* atmosphere — drifts on scroll for depth */}
      <div
        className="grid-pattern pointer-events-none absolute inset-0 opacity-[0.4] will-change-transform"
        style={{ transform: 'translate3d(0, calc(var(--sy, 0) * 0.05px), 0)' }}
      />
      <div
        className="pointer-events-none absolute inset-x-0 -top-40 h-[480px] bg-[radial-gradient(ellipse_60%_60%_at_50%_0%,hsl(var(--primary)/0.16),transparent)] will-change-transform"
        style={{ transform: 'translate3d(0, calc(var(--sy, 0) * 0.18px), 0)' }}
      />

      {/* top bar — floating glass island */}
      <div className="sticky top-0 z-50 pt-4 sm:pt-6">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <header className="group/nav relative mx-auto flex h-14 max-w-5xl items-center justify-between rounded-full border border-white/[0.08] bg-background/50 pl-4 pr-2 backdrop-blur-2xl transition-all duration-500 shadow-[0_1px_0_0_rgba(255,255,255,0.06)_inset,0_0_0_1px_rgba(255,255,255,0.02),0_16px_50px_-20px_rgba(0,0,0,0.85)] hover:border-white/[0.12] hover:bg-background/60">
            {/* hairline sheen along the top edge */}
            <span className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />
            {/* soft inner highlight at the bottom edge — glass depth */}
            <span className="pointer-events-none absolute inset-x-16 bottom-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
            {/* faint cyan wash that lifts on hover */}
            <span className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(120%_140%_at_50%_-40%,hsl(var(--primary)/0.07),transparent_60%)] opacity-0 transition-opacity duration-500 group-hover/nav:opacity-100" />

            <Logo />

            {/* center anchor nav (desktop) */}
            <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 md:flex">
              {NAV_LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  className="rounded-full px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground transition-colors hover:bg-white/[0.05] hover:text-foreground"
                >
                  {l.label}
                </a>
              ))}
            </nav>

            <div className="relative flex items-center gap-1">
              <Link to="/login">
                <Button
                  variant="ghost"
                  size="sm"
                  className="rounded-full px-4 text-muted-foreground hover:bg-white/[0.05] hover:text-foreground"
                >
                  Login
                </Button>
              </Link>
              <Link to="/signup">
                <Button
                  size="sm"
                  className="rounded-full px-4 shadow-[0_0_0_1px_hsl(var(--primary)/0.3),0_6px_20px_-6px_hsl(var(--primary)/0.5)] transition-shadow hover:shadow-[0_0_0_1px_hsl(var(--primary)/0.5),0_8px_28px_-6px_hsl(var(--primary)/0.7)]"
                >
                  Get started
                </Button>
              </Link>
            </div>
          </header>
        </div>
      </div>

      {/* hero */}
      <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 pb-12 pt-16 lg:pt-24">
        <div className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
          {/* copy */}
          <Reveal variant="left">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border/60 bg-muted/30 px-3 py-1">
              <span className="status-indicator high" />
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                Read the fine print before it reads you
              </span>
            </div>
            <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              The risky clauses in any{' '}
              <span className="text-primary glow-text">Terms&nbsp;&amp;&nbsp;Conditions</span>,
              surfaced in seconds.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground lg:text-lg">
              T&amp;C Analyzer reads a Terms of Service or Privacy Policy, flags the clauses that
              disadvantage you — with a severity and a plain-English explanation — and tells you which
              consumer protections it&apos;s <span className="text-foreground">missing</span>.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/signup">
                <Button size="lg" className="glow-primary h-12 px-6 text-sm">
                  Analyze a document
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline" className="h-12 border-border-bright px-6 text-sm">
                  Login
                </Button>
              </Link>
            </div>
            <div className="mt-6 flex items-center gap-2 font-mono text-[11px] text-muted-foreground/70">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500/80" />
              Informational analysis, not legal advice.
            </div>
          </Reveal>

          {/* sample finding preview */}
          <Reveal variant="right" delay={140}>
            <div className="card-interactive overflow-hidden rounded-xl border border-border/50 border-l-4 border-l-red-500 shadow-2xl">
              <div className="flex items-center justify-between border-b border-border/40 bg-card/60 px-4 py-2.5">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  Sample finding
                </span>
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <LogoMark className="h-3.5 w-3.5 text-primary" />
                  <span className="font-mono text-[10px]">live analysis</span>
                </span>
              </div>
              <div className="space-y-4 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Section 7 · Content License
                    </span>
                    <h3 className="mt-1 font-display text-base font-semibold">
                      Perpetual, irrevocable content license
                    </h3>
                  </div>
                  <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-red-500">
                    <AlertTriangle className="h-3 w-3" />
                    <span className="font-mono text-[10px] font-medium">HIGH</span>
                  </span>
                </div>
                <div className="relative pl-3">
                  <span className="absolute bottom-1 left-0 top-1 w-0.5 rounded-full bg-primary/40" />
                  <p className="text-xs italic leading-relaxed text-foreground/70">
                    &ldquo;You grant us a worldwide, royalty-free, perpetual, irrevocable license to
                    use, reproduce, and modify your content…&rdquo;
                  </p>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  The company keeps the right to use what you post{' '}
                  <span className="text-foreground">forever</span> — even after you delete your
                  account. Few services grant themselves this much.
                </p>
              </div>
            </div>
          </Reveal>
        </div>

        {/* stat strip */}
        <Reveal
          as="div"
          delay={120}
          className="mt-16 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border/50 bg-border/30 sm:grid-cols-4"
        >
          {STATS.map((s) => (
            <div key={s.label} className="bg-card/60 px-4 py-5 text-center">
              <div className="font-data text-2xl font-semibold text-primary lg:text-3xl">
                {s.value}
              </div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {s.label}
              </div>
            </div>
          ))}
        </Reveal>
      </section>

      <div id="catches" className="scroll-mt-28" />
      <RiskCatalog />

      <div id="engine" className="scroll-mt-28" />
      <EngineDiagram />

      <div id="evals" className="scroll-mt-28" />
      <EvalReport />

      <SampleFindings />

      <Faq />

      <FinalCta />
    </div>
  );
}
