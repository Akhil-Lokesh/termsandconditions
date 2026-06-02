import {
  Gavel,
  Scale,
  Infinity as InfinityIcon,
  DoorOpen,
  Eye,
  CreditCard,
  MapPin,
} from 'lucide-react';
import { Reveal } from '@/components/Reveal';

/**
 * "What it catches" — the real risk categories the detector screens for.
 * Severity-tinted hairline + icon tile per category, concrete one-liners.
 * Colors follow the app's severity palette (red=high, amber=medium, etc.)
 * but here they convey "category temperature", not a single finding's verdict.
 */

type Tone = 'red' | 'amber' | 'purple' | 'emerald';

const TONE: Record<Tone, { line: string; icon: string; ring: string; glow: string }> = {
  red: {
    line: 'before:bg-red-500',
    icon: 'text-red-500 bg-red-500/10',
    ring: 'ring-red-500/20',
    glow: 'group-hover:shadow-[0_0_24px_-8px_rgba(239,68,68,0.5)]',
  },
  amber: {
    line: 'before:bg-amber-500',
    icon: 'text-amber-500 bg-amber-500/10',
    ring: 'ring-amber-500/20',
    glow: 'group-hover:shadow-[0_0_24px_-8px_rgba(245,158,11,0.5)]',
  },
  purple: {
    line: 'before:bg-purple-500',
    icon: 'text-purple-500 bg-purple-500/10',
    ring: 'ring-purple-500/20',
    glow: 'group-hover:shadow-[0_0_24px_-8px_rgba(168,85,247,0.5)]',
  },
  emerald: {
    line: 'before:bg-emerald-500',
    icon: 'text-emerald-500 bg-emerald-500/10',
    ring: 'ring-emerald-500/20',
    glow: 'group-hover:shadow-[0_0_24px_-8px_rgba(16,185,129,0.5)]',
  },
};

const CATEGORIES: {
  icon: typeof Gavel;
  tone: Tone;
  label: string;
  title: string;
  body: string;
}[] = [
  {
    icon: Scale,
    tone: 'red',
    label: 'Liability',
    title: 'Liability waivers & "as-is" disclaimers',
    body: 'Clauses that strip the company of responsibility for damages, data loss, or downtime — leaving you to absorb the loss.',
  },
  {
    icon: Gavel,
    tone: 'red',
    label: 'Dispute',
    title: 'Forced arbitration & class-action waivers',
    body: 'You surrender your right to sue or join a class action; disputes get pushed into private, company-favorable arbitration.',
  },
  {
    icon: InfinityIcon,
    tone: 'purple',
    label: 'Content',
    title: 'Perpetual content licenses',
    body: 'A worldwide, irrevocable, royalty-free license to your uploads — often surviving long after you delete your account.',
  },
  {
    icon: DoorOpen,
    tone: 'amber',
    label: 'Termination',
    title: 'Unilateral termination',
    body: 'The service can suspend or close your account at any time, for any reason, without notice or an appeal.',
  },
  {
    icon: Eye,
    tone: 'amber',
    label: 'Privacy',
    title: 'Data sharing & behavioral ads',
    body: 'Broad rights to collect, profile, and sell your data to third parties — and to target you with behavioral advertising.',
  },
  {
    icon: CreditCard,
    tone: 'amber',
    label: 'Billing',
    title: 'Auto-renewal & payment traps',
    body: 'Silent auto-renewals, hard-to-cancel subscriptions, non-refundable fees, and unilateral price increases.',
  },
  {
    icon: MapPin,
    tone: 'emerald',
    label: 'Venue',
    title: 'Jurisdiction & venue',
    body: 'Governing-law and venue clauses that force any dispute into a distant, inconvenient, company-chosen court.',
  },
];

export function RiskCatalog() {
  return (
    <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
      <Reveal as="div" className="max-w-2xl">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
          What it catches
        </span>
        <h2 className="mt-3 font-display font-bold text-2xl lg:text-4xl tracking-tight leading-[1.1]">
          The clauses that quietly cost you.
        </h2>
        <p className="mt-4 text-sm lg:text-base text-muted-foreground leading-relaxed">
          Seven families of risk, each matched against curated patterns drawn from real Terms of
          Service and Privacy Policies — flagged with a severity and a reason it matters to you.
        </p>
      </Reveal>

      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CATEGORIES.map((c, i) => {
          const t = TONE[c.tone];
          return (
            <Reveal
              as="article"
              variant="scale"
              delay={i * 70}
              key={c.title}
              className={`group card-interactive relative overflow-hidden rounded-xl border border-border/50 p-5 pl-6
                before:absolute before:left-0 before:top-4 before:bottom-4 before:w-[3px] before:rounded-full ${t.line}
                ${t.glow} transition-shadow duration-300 ${
                i === 6 ? 'sm:col-span-2 lg:col-span-1' : ''
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span
                  className={`inline-grid h-10 w-10 place-items-center rounded-lg ring-1 ${t.icon} ${t.ring}`}
                >
                  <c.icon className="h-5 w-5" />
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/70">
                  {c.label}
                </span>
              </div>
              <h3 className="mt-4 font-display font-semibold text-[15px] leading-snug">
                {c.title}
              </h3>
              <p className="mt-2 text-[13px] text-muted-foreground leading-relaxed">{c.body}</p>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
