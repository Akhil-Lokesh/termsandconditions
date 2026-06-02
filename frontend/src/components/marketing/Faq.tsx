import { Plus } from 'lucide-react';
import { Reveal } from '@/components/Reveal';

/**
 * FAQ — concise, honest answers. Native <details>/<summary> for keyboard +
 * screen-reader accessibility with zero JS; styled as glass rows with a
 * rotating "+" affordance.
 */

const FAQS: { q: string; a: React.ReactNode }[] = [
  {
    q: 'Is this legal advice?',
    a: (
      <>
        No. T&amp;C Analyzer is an <span className="text-foreground">informational</span> tool that
        helps you understand a document faster. It is not a lawyer and does not provide legal advice.
        For decisions with real stakes, consult a qualified attorney.
      </>
    ),
  },
  {
    q: 'What can I upload?',
    a: (
      <>
        Terms of Service and Privacy Policies work best — as a PDF or pasted plain text. It’s built
        for consumer agreements, so the further a document drifts from that, the less tuned the
        analysis will be.
      </>
    ),
  },
  {
    q: 'How does it decide severity?',
    a: (
      <>
        By <span className="text-foreground">consumer harm</span> — how much a clause could actually
        cost you — not by how common the clause is. A term can be industry-standard and still be
        rated high if it’s genuinely bad for you.
      </>
    ),
  },
  {
    q: 'Is my document stored?',
    a: (
      <>
        Your document is processed to produce the analysis and tied to your account so you can revisit
        the findings. It isn’t sold or used to train models, and you stay in control of what you
        upload.
      </>
    ),
  },
];

export function Faq() {
  return (
    <section className="relative z-10 container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
      <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <Reveal as="div" variant="left" className="lg:sticky lg:top-28 lg:self-start">
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
            Questions
          </span>
          <h2 className="mt-3 font-display font-bold text-2xl lg:text-4xl tracking-tight leading-[1.1]">
            The honest answers.
          </h2>
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
            What this tool is, what it isn’t, and how it treats your documents.
          </p>
        </Reveal>

        <Reveal
          as="div"
          variant="up"
          delay={80}
          className="divide-y divide-border/40 overflow-hidden rounded-2xl border border-white/[0.06] bg-card/30 backdrop-blur-xl shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset]"
        >
          {FAQS.map((f) => (
            <details
              key={f.q}
              className="group/faq px-5 py-4 transition-colors hover:bg-white/[0.02] lg:px-6"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 [&::-webkit-details-marker]:hidden">
                <span className="font-display font-semibold text-[15px] lg:text-base">{f.q}</span>
                <span className="inline-grid h-7 w-7 shrink-0 place-items-center rounded-full border border-border/60 bg-muted/30 text-muted-foreground transition-all duration-300 group-open/faq:rotate-45 group-open/faq:border-primary/40 group-open/faq:text-primary">
                  <Plus className="h-3.5 w-3.5" />
                </span>
              </summary>
              <p className="mt-3 max-w-prose text-[13px] leading-relaxed text-muted-foreground">
                {f.a}
              </p>
            </details>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
