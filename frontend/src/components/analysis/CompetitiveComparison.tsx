import { CompetitiveBenchmark } from '@/types';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Building2,
  AlertTriangle,
  Shield,
  ShieldOff,
  Lightbulb,
  BarChart3
} from 'lucide-react';

interface CompetitiveComparisonProps {
  benchmark: CompetitiveBenchmark;
  documentRiskScore?: number;
}

export const CompetitiveComparison = ({ benchmark, documentRiskScore }: CompetitiveComparisonProps) => {
  // Color coding based on percentile (lower is better)
  const getPercentileColor = (percentile: number) => {
    if (percentile <= 30) return { text: 'text-emerald-500', bg: 'bg-emerald-500', bgLight: 'bg-emerald-500/10' };
    if (percentile <= 60) return { text: 'text-amber-500', bg: 'bg-amber-500', bgLight: 'bg-amber-500/10' };
    return { text: 'text-red-500', bg: 'bg-red-500', bgLight: 'bg-red-500/10' };
  };

  const percentileColors = getPercentileColor(benchmark.percentile_rank);

  const getComparisonIcon = () => {
    switch (benchmark.risk_comparison) {
      case 'better': return <TrendingDown className="h-4 w-4 text-emerald-500" />;
      case 'worse': return <TrendingUp className="h-4 w-4 text-red-500" />;
      default: return <Minus className="h-4 w-4 text-amber-500" />;
    }
  };

  const getComparisonLabel = () => {
    switch (benchmark.risk_comparison) {
      case 'better': return 'Better than average';
      case 'worse': return 'Worse than average';
      default: return 'About average';
    }
  };

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Industry Comparison Header */}
      <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-6">
        <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] mb-3 lg:mb-4">
          <BarChart3 className="h-3 w-3" />
          <span>Industry Comparison</span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 lg:gap-6">
          {/* Percentile Badge */}
          <div className="flex items-center gap-3 lg:gap-4">
            <div className={`p-3 lg:p-4 rounded-xl ${percentileColors.bgLight}`}>
              <span className={`text-2xl lg:text-3xl font-display font-bold ${percentileColors.text}`}>
                {benchmark.percentile_rank}
              </span>
              <span className={`text-xs lg:text-sm ${percentileColors.text}`}>th</span>
            </div>
            <div>
              <p className="font-display font-semibold text-sm lg:text-base text-foreground">
                Percentile Ranking
              </p>
              <p className="text-xs lg:text-sm text-muted-foreground mt-0.5">
                {benchmark.percentile_rank <= 30
                  ? 'Better than most competitors'
                  : benchmark.percentile_rank <= 60
                  ? 'Similar to industry average'
                  : 'Worse than most competitors'}
              </p>
            </div>
          </div>

          {/* Risk Score Comparison */}
          <div className="flex items-center gap-4 lg:gap-6 pt-3 lg:pt-0 border-t lg:border-t-0 border-border/30">
            <div className="text-center">
              <p className="text-lg lg:text-2xl font-data font-bold text-foreground">
                {documentRiskScore?.toFixed(1) || '-'}
              </p>
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mt-0.5">
                This Doc
              </p>
            </div>
            <div className="flex items-center gap-2">
              {getComparisonIcon()}
              <span className="text-xs text-muted-foreground">{getComparisonLabel()}</span>
            </div>
            <div className="text-center">
              <p className="text-lg lg:text-2xl font-data font-bold text-muted-foreground">
                {benchmark.industry_average_risk.toFixed(1)}
              </p>
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mt-0.5">
                Industry Avg
              </p>
            </div>
          </div>
        </div>

        {/* Percentile scale */}
        <div className="mt-5 lg:mt-6">
          <div className="flex justify-between text-[9px] lg:text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-1.5">
            <span className="text-emerald-400">Best (0)</span>
            <span className="text-amber-400">Average</span>
            <span className="text-red-400">Worst (100)</span>
          </div>
          <div className="relative h-2">
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-emerald-500/40 via-amber-500/40 to-red-500/40" />
            <div
              className={`absolute top-1/2 -translate-y-1/2 h-3.5 w-3.5 -ml-1.5 rounded-full border-2 border-background ${percentileColors.bg} shadow-lg transition-all duration-700`}
              style={{ left: `${Math.max(0, Math.min(100, benchmark.percentile_rank))}%` }}
              title={`${benchmark.percentile_rank}th percentile`}
            />
          </div>
        </div>

        {/* Summary */}
        <div className="mt-4 pt-4 border-t border-border/30">
          <p className="text-xs lg:text-sm text-muted-foreground italic leading-relaxed">
            {benchmark.summary}
          </p>
        </div>
      </div>

      {/* Better Alternatives */}
      {benchmark.better_alternatives.length > 0 && (
        <div className="card-interactive rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 lg:p-5">
          <div className="flex items-center gap-2 text-emerald-400 text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] mb-3 lg:mb-4">
            <Shield className="h-3 w-3" />
            <span>Lower-Risk Alternatives</span>
            <span className="ml-auto font-data text-muted-foreground">{benchmark.better_alternatives.length}</span>
          </div>
          <div className="space-y-2">
            {benchmark.better_alternatives.map((alt, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between gap-3 p-2.5 lg:p-3 rounded-lg bg-background/50 border border-border/40"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="grid place-items-center h-5 w-5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-data text-emerald-400 shrink-0">
                    {idx + 1}
                  </span>
                  <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-sm font-medium text-foreground truncate">{alt.company_name}</span>
                </div>
                <div className="flex items-baseline gap-1 shrink-0">
                  <span className="text-sm lg:text-base font-data font-bold text-emerald-400">{alt.avg_risk_score.toFixed(1)}</span>
                  <span className="text-[10px] font-mono text-muted-foreground">/10</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unique Risks (what's present & risky) & Missing Protections (what's absent) */}
      <div className="grid md:grid-cols-2 gap-4 lg:gap-6">
        {/* Unique Risks — present & risky → solid red treatment */}
        {benchmark.unique_risks.length > 0 && (
          <div className="card-interactive rounded-xl border border-red-500/20 bg-red-500/5 p-4 lg:p-5">
            <div className="flex items-center gap-2 text-red-400 text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] mb-3 lg:mb-4">
              <AlertTriangle className="h-3 w-3" />
              <span>Unique Risks vs Peers</span>
              <span className="ml-auto font-data text-muted-foreground">{benchmark.unique_risks.length}</span>
            </div>
            <ul className="space-y-2">
              {benchmark.unique_risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2.5 text-xs lg:text-sm text-foreground/85">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
                  <span className="leading-relaxed">{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Missing Protections — ABSENT → ghosted, dashed "what's missing" treatment */}
        {benchmark.missing_protections.length > 0 && (
          <div className="rounded-xl border border-dashed border-amber-500/30 bg-amber-500/[0.04] p-4 lg:p-5">
            <div className="flex items-center gap-2 text-amber-400 text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] mb-3 lg:mb-4">
              <ShieldOff className="h-3 w-3" />
              <span>Protections You Don't Get</span>
              <span className="ml-auto font-data text-muted-foreground">{benchmark.missing_protections.length}</span>
            </div>
            <ul className="space-y-2">
              {benchmark.missing_protections.map((protection, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2.5 text-xs lg:text-sm text-muted-foreground"
                >
                  <span className="mt-0.5 h-4 w-4 grid place-items-center rounded-full border border-dashed border-amber-500/50 text-amber-400/80 shrink-0 text-[10px] leading-none">
                    ×
                  </span>
                  <span className="leading-relaxed line-through decoration-amber-500/30 decoration-1">
                    {protection}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Recommendations */}
      {benchmark.recommendations.length > 0 && (
        <div className="card-interactive rounded-xl border border-primary/20 bg-primary/5 p-4 lg:p-5">
          <div className="flex items-center gap-2 text-primary text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] mb-3 lg:mb-4">
            <Lightbulb className="h-3 w-3" />
            <span>Recommendations</span>
          </div>
          <ul className="space-y-2.5 lg:space-y-3">
            {benchmark.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs lg:text-sm text-foreground/90">
                <span className="grid place-items-center h-5 w-5 rounded bg-primary/10 border border-primary/20 text-[10px] font-data text-primary shrink-0">
                  {idx + 1}
                </span>
                <span className="leading-relaxed pt-0.5">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
