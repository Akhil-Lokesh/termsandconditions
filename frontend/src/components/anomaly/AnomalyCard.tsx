import { Anomaly } from '@/types';
import { SeverityBadge } from './SeverityBadge';
import { FeedbackButtons } from './FeedbackButtons';
import { Hash, Tag, TrendingUp, Quote, Lightbulb, AlertCircle } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface AnomalyCardProps {
  anomaly: Anomaly;
}

const SEVERITY_ACCENT: Record<Anomaly['severity'], string> = {
  critical: 'border-l-purple-500',
  high: 'border-l-red-500',
  medium: 'border-l-amber-500',
  low: 'border-l-emerald-500',
};

export const AnomalyCard = ({ anomaly }: AnomalyCardProps) => {
  const prevalenceLabel =
    anomaly.prevalence < 0.3 ? 'Rare' : anomaly.prevalence < 0.7 ? 'Uncommon' : 'Common';

  const prevalenceColor =
    anomaly.prevalence < 0.3
      ? 'text-red-400'
      : anomaly.prevalence < 0.7
      ? 'text-amber-400'
      : 'text-emerald-400';

  const prevalenceChip =
    anomaly.prevalence < 0.3
      ? 'bg-red-500/10 text-red-400 border-red-500/20'
      : anomaly.prevalence < 0.7
      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

  // risk_category is present on the detail payload; absent on the list payload.
  const category = anomaly.risk_category && anomaly.risk_category !== 'other'
    ? anomaly.risk_category.replace(/_/g, ' ')
    : null;

  const clauseRef = [anomaly.section, anomaly.clause_number]
    .filter(Boolean)
    .join(' · ');

  return (
    <article
      className={`group relative card-interactive rounded-xl border border-border/50 border-l-[3px] ${SEVERITY_ACCENT[anomaly.severity]} overflow-hidden`}
    >
      {/* Header */}
      <div className="p-4 lg:p-5 border-b border-border/30">
        <div className="flex items-start justify-between gap-3 lg:gap-4">
          <div className="flex-1 min-w-0">
            {/* Clause reference + category */}
            <div className="flex flex-wrap items-center gap-2 mb-2">
              {clauseRef && (
                <span className="inline-flex items-center gap-1.5 text-[10px] lg:text-xs font-mono text-muted-foreground uppercase tracking-wider max-w-full truncate">
                  <Hash className="h-3 w-3 shrink-0" />
                  <span className="truncate">{clauseRef}</span>
                </span>
              )}
              {category && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] lg:text-[10px] font-mono uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
                  {category}
                </span>
              )}
            </div>
            <h3 className="font-display font-semibold text-sm lg:text-base text-foreground leading-snug">
              {anomaly.risk_title || 'Risk Detected'}
            </h3>
          </div>
          <div className="shrink-0">
            <SeverityBadge severity={anomaly.severity} />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 lg:p-5 space-y-4 lg:space-y-5">
        {/* Quoted clause */}
        <figure className="relative rounded-lg bg-background/50 border border-border/40 p-3 lg:p-4">
          <Quote className="absolute -top-2 left-3 h-4 w-4 text-primary/40 bg-card rounded-full" />
          <figcaption className="mb-1.5 text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
            Original Clause
          </figcaption>
          <blockquote className="text-xs lg:text-sm text-foreground/80 italic leading-relaxed">
            "{anomaly.clause_text}"
          </blockquote>
        </figure>

        {/* Explanation */}
        <div>
          <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1.5">
            Analysis
          </h4>
          <p className="text-xs lg:text-sm text-foreground/70 leading-relaxed">
            {anomaly.explanation}
          </p>
        </div>

        {/* Impact + recommendation grid */}
        {(anomaly.consumer_impact || anomaly.recommendation) && (
          <div className="grid sm:grid-cols-2 gap-3 lg:gap-4">
            {anomaly.consumer_impact && (
              <div className="rounded-lg bg-amber-500/[0.06] border border-amber-500/20 p-3 lg:p-4">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <AlertCircle className="h-3.5 w-3.5 lg:h-4 lg:w-4 text-amber-400" />
                  <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-amber-400">
                    Why It Matters
                  </h4>
                </div>
                <p className="text-xs lg:text-sm text-foreground/90 leading-relaxed">
                  {anomaly.consumer_impact}
                </p>
              </div>
            )}

            {anomaly.recommendation && (
              <div className="rounded-lg bg-emerald-500/[0.06] border border-emerald-500/20 p-3 lg:p-4">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Lightbulb className="h-3.5 w-3.5 lg:h-4 lg:w-4 text-emerald-400" />
                  <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-emerald-400">
                    What You Can Do
                  </h4>
                </div>
                <p className="text-xs lg:text-sm text-foreground/90 leading-relaxed">
                  {anomaly.recommendation}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Risk Flags */}
        {anomaly.risk_flags && anomaly.risk_flags.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Tag className="h-3 w-3 lg:h-3.5 lg:w-3.5 text-muted-foreground" />
              <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                Risk Indicators
              </h4>
            </div>
            <div className="flex flex-wrap gap-1.5 lg:gap-2">
              {anomaly.risk_flags.map((flag) => (
                <span
                  key={flag}
                  className="px-2 lg:px-2.5 py-0.5 lg:py-1 text-[10px] lg:text-xs font-mono rounded-full bg-muted/60 text-foreground/70 border border-border/50"
                >
                  {flag.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Prevalence */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-3 lg:pt-4 border-t border-border/30">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
            <span className="text-xs lg:text-sm">Prevalence in standard T&Cs</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`font-data text-sm lg:text-base font-medium ${prevalenceColor}`}>
              {formatPercentage(anomaly.prevalence)}
            </span>
            <span
              className={`text-[10px] lg:text-xs font-mono px-1.5 lg:px-2 py-0.5 rounded border ${prevalenceChip}`}
            >
              {prevalenceLabel}
            </span>
          </div>
        </div>

        {/* Feedback Buttons (Layer 5 — active learning) */}
        <FeedbackButtons anomalyId={anomaly.id} currentSeverity={anomaly.severity} />
      </div>
    </article>
  );
};
