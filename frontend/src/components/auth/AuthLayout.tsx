import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { AlertTriangle, ShieldCheck, ScanLine, FileCheck2 } from 'lucide-react';

const POINTS = [
  { icon: ScanLine, text: '~41 curated risk patterns, matched clause by clause' },
  { icon: FileCheck2, text: 'Flags the consumer protections a fair agreement is missing' },
  { icon: ShieldCheck, text: 'Severity by consumer harm — not how common the clause is' },
];

/**
 * Auth shell. One atmospheric page (a single grid + glow layer spans the whole
 * viewport). The logo sits atop a vertically-centered group; below it the brand
 * story and the form share the same top edge, so a short form (e.g. login) is
 * anchored to the top rather than floating in the middle.
 */
export const AuthLayout = ({ children }: { children: ReactNode }) => (
  <div className="relative min-h-screen overflow-hidden bg-background">
    {/* unified atmosphere — one continuous background, no seam */}
    <div className="grid-pattern pointer-events-none absolute inset-0 opacity-[0.18]" />
    <div className="pointer-events-none absolute inset-x-0 -top-40 h-[460px] bg-[radial-gradient(ellipse_55%_55%_at_50%_0%,hsl(var(--primary)/0.1),transparent)]" />
    <div className="pointer-events-none absolute left-[18%] top-1/3 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,hsl(var(--primary)/0.1),transparent_70%)]" />
    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-background to-transparent" />

    {/* vertically-centered group: logo on top, then the two top-aligned columns */}
    <div className="relative z-10 mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 py-12 lg:px-12">
      <div className="flex items-center justify-center gap-12 lg:gap-20">
        {/* LEFT — brand story (desktop only) — fixed width, never balloons */}
        <section className="hidden flex-col lg:flex lg:w-[30rem] lg:flex-none">
          <Link to="/" className="mb-8 w-fit" aria-label="T&C Analyzer — home">
            <Logo />
          </Link>
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-primary">
            Contract risk intelligence
          </span>
          <h2 className="mt-5 font-display text-4xl font-bold leading-[1.1] tracking-tight xl:text-[2.75rem]">
            Know exactly what you&apos;re agreeing to.
          </h2>
          <p className="mt-5 text-base leading-relaxed text-muted-foreground">
            Upload a Terms of Service or Privacy Policy and get the risky clauses — by severity,
            in plain English — plus the protections it leaves out.
          </p>

          {/* sample finding — shows the product at a glance */}
          <div className="card-interactive mt-8 rounded-xl border border-border/50 border-l-4 border-l-red-500 p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Section 7 · Content License
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-red-500">
                <AlertTriangle className="h-3 w-3" />
                <span className="font-mono text-[10px] font-medium">HIGH</span>
              </span>
            </div>
            <p className="mt-2 font-display text-base font-semibold">Perpetual, irrevocable content license</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              They keep the right to use what you post <span className="text-foreground">forever</span> — even
              after you delete your account.
            </p>
          </div>

          <ul className="mt-8 space-y-4">
            {POINTS.map((p) => (
              <li key={p.text} className="flex items-start gap-3.5 text-base text-muted-foreground">
                <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-primary/10 text-primary ring-1 ring-inset ring-primary/20">
                  <p.icon className="h-4 w-4" />
                </span>
                <span className="leading-snug">{p.text}</span>
              </li>
            ))}
          </ul>

          <div className="mt-10 flex items-center gap-2 font-mono text-xs text-muted-foreground/70">
            <ShieldCheck className="h-4 w-4 text-emerald-500/80" />
            Informational analysis, not legal advice.
          </div>
        </section>

        {/* RIGHT — form — fixed wide width on desktop */}
        <div className="flex w-full max-w-md flex-col items-center lg:w-[34rem] lg:max-w-none lg:flex-none lg:items-stretch">
          {/* logo on mobile (brand panel is hidden) */}
          <Link to="/" className="mb-8 lg:hidden" aria-label="T&C Analyzer — home">
            <Logo />
          </Link>
          {children}
        </div>
      </div>
    </div>
  </div>
);
