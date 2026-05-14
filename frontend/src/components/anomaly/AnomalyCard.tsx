import { Anomaly } from '@/types';
import { SeverityBadge } from './SeverityBadge';
import { FeedbackButtons } from './FeedbackButtons';
import { FileText, Tag, TrendingUp, Quote, Lightbulb, AlertCircle } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface AnomalyCardProps {
  anomaly: Anomaly;
}

export const AnomalyCard = ({ anomaly }: AnomalyCardProps) => {
  const severityColors = {
    critical: 'border-l-purple-500',
    high: 'border-l-red-500',
    medium: 'border-l-amber-500',
    low: 'border-l-emerald-500',
  };

  const prevalenceLabel = anomaly.prevalence < 0.3 ? 'Rare' :
                          anomaly.prevalence < 0.7 ? 'Uncommon' : 'Common';

  const prevalenceColor = anomaly.prevalence < 0.3 ? 'text-red-500' :
                          anomaly.prevalence < 0.7 ? 'text-amber-500' : 'text-emerald-500';

  return (
    <div className={`card-interactive rounded-xl border border-border/50 border-l-4 ${severityColors[anomaly.severity]} overflow-hidden`}>
      {/* Header */}
      <div className="p-4 lg:p-5 border-b border-border/30">
        <div className="flex items-start justify-between gap-3 lg:gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 lg:mb-2">
              <div className="p-1 lg:p-1.5 rounded bg-muted/50">
                <FileText className="h-3 w-3 lg:h-3.5 lg:w-3.5 text-muted-foreground" />
              </div>
              <span className="text-[10px] lg:text-xs font-mono text-muted-foreground uppercase tracking-wider truncate">
                {anomaly.section}
                {anomaly.clause_number && ` - ${anomaly.clause_number}`}
              </span>
            </div>
            <h3 className="font-display font-semibold text-sm lg:text-base text-foreground">Risk Detected</h3>
          </div>
          <SeverityBadge severity={anomaly.severity} />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 lg:p-5 space-y-4 lg:space-y-5">
        {/* Clause Text */}
        <div className="relative">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary/30 rounded-full" />
          <div className="pl-3 lg:pl-4 py-1.5 lg:py-2">
            <div className="flex items-center gap-1.5 lg:gap-2 mb-1.5 lg:mb-2 text-muted-foreground">
              <Quote className="h-3 w-3" />
              <span className="text-[10px] lg:text-xs font-mono uppercase tracking-wider">Original Clause</span>
            </div>
            <p className="text-xs lg:text-sm text-foreground/80 italic leading-relaxed">
              "{anomaly.clause_text}"
            </p>
          </div>
        </div>

        {/* Explanation */}
        <div>
          <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1.5 lg:mb-2">
            Analysis
          </h4>
          <p className="text-xs lg:text-sm text-muted-foreground leading-relaxed">
            {anomaly.explanation}
          </p>
        </div>

        {/* Consumer Impact */}
        {anomaly.consumer_impact && (
          <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-3 lg:p-4">
            <div className="flex items-center gap-1.5 lg:gap-2 mb-1.5 lg:mb-2">
              <AlertCircle className="h-3.5 w-3.5 lg:h-4 lg:w-4 text-amber-500" />
              <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-amber-500">
                Impact on You
              </h4>
            </div>
            <p className="text-xs lg:text-sm text-foreground/90 leading-relaxed">
              {anomaly.consumer_impact}
            </p>
          </div>
        )}

        {/* Recommendation */}
        {anomaly.recommendation && (
          <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-3 lg:p-4">
            <div className="flex items-center gap-1.5 lg:gap-2 mb-1.5 lg:mb-2">
              <Lightbulb className="h-3.5 w-3.5 lg:h-4 lg:w-4 text-emerald-500" />
              <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-emerald-500">
                What You Can Do
              </h4>
            </div>
            <p className="text-xs lg:text-sm text-foreground/90 leading-relaxed">
              {anomaly.recommendation}
            </p>
          </div>
        )}

        {/* Risk Flags */}
        {anomaly.risk_flags && anomaly.risk_flags.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 lg:gap-2 mb-2 lg:mb-3">
              <Tag className="h-3 w-3 lg:h-3.5 lg:w-3.5 text-muted-foreground" />
              <h4 className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                Risk Indicators
              </h4>
            </div>
            <div className="flex flex-wrap gap-1.5 lg:gap-2">
              {anomaly.risk_flags.map((flag) => (
                <span
                  key={flag}
                  className="px-2 lg:px-2.5 py-0.5 lg:py-1 text-[10px] lg:text-xs font-mono rounded-full bg-primary/10 text-primary border border-primary/20"
                >
                  {flag.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Prevalence Score */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-3 lg:pt-4 border-t border-border/30">
          <div className="flex items-center gap-1.5 lg:gap-2 text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
            <span className="text-xs lg:text-sm">Prevalence in standard T&Cs</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`font-data text-sm lg:text-base font-medium ${prevalenceColor}`}>
              {formatPercentage(anomaly.prevalence)}
            </span>
            <span className={`text-[10px] lg:text-xs font-mono px-1.5 lg:px-2 py-0.5 rounded ${
              anomaly.prevalence < 0.3 ? 'bg-red-500/10 text-red-500' :
              anomaly.prevalence < 0.7 ? 'bg-amber-500/10 text-amber-500' :
              'bg-emerald-500/10 text-emerald-500'
            }`}>
              {prevalenceLabel}
            </span>
          </div>
        </div>

        {/* Feedback Buttons (Layer 5 — active learning) */}
        <FeedbackButtons
          anomalyId={anomaly.id}
          currentSeverity={anomaly.severity}
        />
      </div>
    </div>
  );
};
