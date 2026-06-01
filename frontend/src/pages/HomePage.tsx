import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Logo, LogoMark } from '@/components/Logo';
import {
  ScanLine,
  ShieldCheck,
  MessagesSquare,
  ArrowRight,
  AlertTriangle,
  Upload,
  FileSearch,
  ListChecks,
} from 'lucide-react';

const STATS = [
  { value: '41', label: 'curated risk patterns' },
  { value: '4', label: 'severity tiers' },
  { value: '2-pass', label: 'LLM detection + ranker' },
  { value: 'public', label: 'benchmark-evaluated' },
];

const FEATURES = [
  {
    icon: ScanLine,
    title: 'Risky-clause detection',
    body: 'A checklist of curated risk patterns is matched against every clause — perpetual content licenses, forced arbitration, termination-on-suspicion — each flagged with a severity and a plain-English reason it matters to you.',
  },
  {
    icon: ShieldCheck,
    title: 'Missing-protection scan',
    body: 'Just as important as the bad clauses: the protections a fair agreement should have but doesn’t — breach notification, advance notice of changes, an appeal for account termination.',
  },
  {
    icon: MessagesSquare,
    title: 'Ask the document',
    body: 'Query any uploaded agreement in plain language and get answers grounded in the actual text, with citations back to the exact clauses.',
  },
];

const STEPS = [
  { icon: Upload, title: 'Upload', body: 'Drop in a Terms of Service or Privacy Policy — PDF or pasted text.' },
  { icon: FileSearch, title: 'Analyze', body: 'Each clause is matched against the risk catalog and screened for missing protections.' },
  { icon: ListChecks, title: 'Review', body: 'Findings ranked by severity, in plain English, with the clause and why it’s risky.' },
];

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* atmosphere */}
      <div className="grid-pattern pointer-events-none absolute inset-0 opacity-[0.4]" />
      <div className="pointer-events-none absolute inset-x-0 -top-40 h-[480px] bg-[radial-gradient(ellipse_60%_60%_at_50%_0%,hsl(var(--primary)/0.16),transparent)]" />

      {/* top bar */}
      <header className="relative z-10 border-b border-border/40 backdrop-blur-sm">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <Logo />
          <div className="flex items-center gap-2">
            <Link to="/login">
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                Login
              </Button>
            </Link>
            <Link to="/signup">
              <Button size="sm" className="glow-primary">Get started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 pt-16 lg:pt-24 pb-12">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-12 lg:gap-16 items-center">
          {/* copy */}
          <div className="animate-slide-up">
            <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-muted/30 px-3 py-1 mb-6">
              <span className="status-indicator high" />
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                Read the fine print before it reads you
              </span>
            </div>
            <h1 className="font-display font-bold tracking-tight text-4xl sm:text-5xl lg:text-6xl leading-[1.05]">
              The risky clauses in any{' '}
              <span className="text-primary glow-text">Terms&nbsp;&amp;&nbsp;Conditions</span>,
              surfaced in seconds.
            </h1>
            <p className="mt-6 text-base lg:text-lg text-muted-foreground max-w-xl leading-relaxed">
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
                <Button size="lg" variant="outline" className="h-12 px-6 text-sm border-border-bright">
                  Login
                </Button>
              </Link>
            </div>
          </div>

          {/* sample finding preview */}
          <div className="animate-slide-up stagger-2">
            <div className="card-interactive rounded-xl border border-border/50 border-l-4 border-l-red-500 overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between border-b border-border/40 px-4 py-2.5 bg-card/60">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  Sample finding
                </span>
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <LogoMark className="h-3.5 w-3.5 text-primary" />
                  <span className="font-mono text-[10px]">live analysis</span>
                </span>
              </div>
              <div className="p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Section 7 · Content License
                    </span>
                    <h3 className="font-display font-semibold text-base mt-1">
                      Perpetual, irrevocable content license
                    </h3>
                  </div>
                  <span className="shrink-0 inline-flex items-center gap-1.5 rounded-full border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-red-500">
                    <AlertTriangle className="h-3 w-3" />
                    <span className="font-mono text-[10px] font-medium">HIGH</span>
                  </span>
                </div>
                <div className="relative pl-3">
                  <span className="absolute left-0 top-1 bottom-1 w-0.5 rounded-full bg-primary/40" />
                  <p className="text-xs text-foreground/70 italic leading-relaxed">
                    &ldquo;You grant us a worldwide, royalty-free, perpetual, irrevocable license to use,
                    reproduce, and modify your content…&rdquo;
                  </p>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  The company keeps the right to use what you post <span className="text-foreground">forever</span> —
                  even after you delete your account. Few services grant themselves this much.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* stat strip */}
        <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-px rounded-xl border border-border/50 overflow-hidden bg-border/30">
          {STATS.map((s) => (
            <div key={s.label} className="bg-card/60 px-4 py-5 text-center">
              <div className="font-data text-2xl lg:text-3xl font-semibold text-primary">{s.value}</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* features */}
      <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-20">
        <div className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">What it does</span>
          <h2 className="mt-3 font-display font-bold text-2xl lg:text-3xl tracking-tight">
            Two ways a contract can hurt you — both covered.
          </h2>
        </div>
        <div className="mt-10 grid md:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <div
              key={f.title}
              className={`card-interactive rounded-xl border border-border/50 p-6 animate-slide-up stagger-${i + 1}`}
            >
              <div className="inline-grid place-items-center h-11 w-11 rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display font-semibold text-lg">{f.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* how it works */}
      <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="rounded-2xl border border-border/50 bg-card/40 p-8 lg:p-12">
          <div className="text-center max-w-xl mx-auto">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">How it works</span>
            <h2 className="mt-3 font-display font-bold text-2xl lg:text-3xl tracking-tight">
              From upload to verdict in three steps.
            </h2>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-8 lg:gap-12">
            {STEPS.map((s, i) => (
              <div key={s.title} className="relative text-center">
                <div className="mx-auto inline-grid place-items-center h-14 w-14 rounded-xl bg-gradient-to-br from-primary to-accent text-primary-foreground">
                  <s.icon className="h-6 w-6" />
                </div>
                <div className="mt-4 flex items-center justify-center gap-2">
                  <span className="font-data text-xs text-primary">0{i + 1}</span>
                  <h4 className="font-display font-semibold">{s.title}</h4>
                </div>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">{s.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Link to="/signup">
              <Button size="lg" className="glow-primary h-12 px-7">
                Get started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* footer */}
      <footer className="relative z-10 border-t border-border/40">
        <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 py-8">
          <Logo showWordmark />
          <p className="font-mono text-[11px] text-muted-foreground text-center sm:text-right">
            Informational analysis, not legal advice. Built as an engineering portfolio project.
          </p>
        </div>
      </footer>
    </div>
  );
}
