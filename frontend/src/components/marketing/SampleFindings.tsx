import { AlertTriangle, ShieldAlert } from 'lucide-react';
import { LogoMark } from '@/components/Logo';
import { Reveal } from '@/components/Reveal';

/**
 * Sample findings showcase — illustrative cards styled like the app's real
 * findings (severity color rail, mono section label, quoted clause, plain-English
 * "why it matters"). Realistic but clearly examples.
 */

type Sev = 'high' | 'medium';

const SEV: Record<Sev, { label: string; text: string; bd: string; bg: string; rail: string }> = {
  high: {
    label: 'HIGH',
    text: 'text-red-500',
    bd: 'border-red-500/20',
    bg: 'bg-red-500/10',
    rail: 'border-l-red-500',
  },
  medium: {
    label: 'MEDIUM',
    text: 'text-amber-500',
    bd: 'border-amber-500/20',
    bg: 'bg-amber-500/10',
    rail: 'border-l-amber-500',
  },
};

const FINDINGS: {
  sev: Sev;
  section: string;
  title: string;
  quote: string;
  why: React.ReactNode;
}[] = [
  {
    sev: 'high',
    section: 'Section 12 · Dispute Resolution',
    title: 'Forced arbitration & class-action waiver',
    quote:
      'You agree to resolve any dispute through binding individual arbitration and waive any right to a jury trial or to participate in a class action.',
    why: (
      <>
        You give up the courtroom <span className="text-foreground">and</span> the ability to band
        together with others — the two things that make holding a large company accountable
        affordable.
      </>
    ),
  },
  {
    sev: 'high',
    section: 'Section 7 · Content License',
    title: 'Perpetual, irrevocable content license',
    quote:
      'You grant us a worldwide, royalty-free, perpetual, irrevocable license to use, reproduce, and modify your content.',
    why: (
      <>
        The company keeps the right to use what you post{' '}
        <span className="text-foreground">forever</span> — even after you delete your account. Few
        services grant themselves this much.
      </>
    ),
  },
  {
    sev: 'medium',
    section: 'Section 4 · Billing',
    title: 'Silent auto-renewal',
    quote:
      'Your subscription will automatically renew at the then-current rate unless cancelled at least 30 days before the renewal date.',
    why: (
      <>
        Renews itself at whatever the price becomes, with a long cancellation window that’s easy to
        miss — a common way recurring charges slip through.
      </>
    ),
  },
];

export function SampleFindings() {
  return (
    <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
      <Reveal as="div" className="max-w-2xl">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
          What you’ll see
        </span>
        <h2 className="mt-3 font-display font-bold text-2xl lg:text-4xl tracking-tight leading-[1.1]">
          Every finding, in plain English.
        </h2>
        <p className="mt-4 text-sm lg:text-base text-muted-foreground leading-relaxed">
          No legalese, no scores you can’t interpret. The exact clause, a severity, and a sentence on
          why it matters to you. Examples below.
        </p>
      </Reveal>

      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        {FINDINGS.map((f, i) => {
          const s = SEV[f.sev];
          return (
            <Reveal
              as="article"
              variant="up"
              delay={i * 110}
              key={f.title}
              className={`card-interactive flex flex-col overflow-hidden rounded-xl border border-border/50 border-l-4 ${s.rail}`}
            >
              <div className="flex items-center justify-between border-b border-border/40 bg-card/60 px-4 py-2.5">
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  Finding
                </span>
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <LogoMark className="h-3.5 w-3.5 text-primary" />
                  <span className="font-mono text-[10px]">example</span>
                </span>
              </div>

              <div className="flex flex-1 flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      {f.section}
                    </span>
                    <h3 className="mt-1 font-display font-semibold text-[15px] leading-snug">
                      {f.title}
                    </h3>
                  </div>
                  <span
                    className={`shrink-0 inline-flex items-center gap-1.5 rounded-full border ${s.bd} ${s.bg} px-2.5 py-1 ${s.text}`}
                  >
                    {f.sev === 'high' ? (
                      <AlertTriangle className="h-3 w-3" />
                    ) : (
                      <ShieldAlert className="h-3 w-3" />
                    )}
                    <span className="font-mono text-[10px] font-medium">{s.label}</span>
                  </span>
                </div>

                <div className="relative mt-4 pl-3">
                  <span className="absolute left-0 top-1 bottom-1 w-0.5 rounded-full bg-primary/40" />
                  <p className="text-xs italic leading-relaxed text-foreground/70">
                    &ldquo;{f.quote}&rdquo;
                  </p>
                </div>

                <p className="mt-4 text-xs leading-relaxed text-muted-foreground">{f.why}</p>
              </div>
            </Reveal>
          );
        })}
      </div>

      <p className="mt-5 font-mono text-[11px] text-muted-foreground/60">
        Illustrative examples — your findings come from your own uploaded document.
      </p>
    </section>
  );
}
