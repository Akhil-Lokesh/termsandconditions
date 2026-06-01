import { Anomaly } from '@/types';
import {
  Loader2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Gauge,
  ListChecks,
  ShieldX,
} from 'lucide-react';

type RiskLevel = 'analyzing' | 'critical' | 'high' | 'medium' | 'low';

interface RiskSummaryHeaderProps {
  riskLevel: RiskLevel;
  riskScore?: number | null;
  isAnalyzing: boolean;
  anomalies: Anomaly[];
  /** Count of missing consumer protections, if surfaced by the benchmark. */
  missingProtectionsCount?: number;
}

interface SeveritySegment {
  key: 'critical' | 'high' | 'medium' | 'low';
  label: string;
  count: number;
  /** Tailwind text color token */
  text: string;
  /** Tailwind background (solid) for the distribution bar */
  bar: string;
  /** Soft background for the chip */
  chipBg: string;
  /** Border for the chip */
  chipBorder: string;
  /** Small accent dot */
  dot: string;
}

const RISK_META: Record<
  RiskLevel,
  {
    label: string;
    sub: string;
    text: string;
    ring: string;
    glow: string;
    Icon: typeof Shield;
  }
> = {
  analyzing: {
    label: 'Analyzing',
    sub: 'Scanning clauses for risky patterns',
    text: 'text-primary',
    ring: 'border-primary/30',
    glow: 'shadow-[0_0_30px_-8px_hsl(var(--primary)/0.45)]',
    Icon: Loader2,
  },
  critical: {
    label: 'Critical Risk',
    sub: 'Contains severe, consumer-hostile clauses',
    text: 'text-purple-400',
    ring: 'border-purple-500/40',
    glow: 'shadow-[0_0_34px_-8px_rgba(168,85,247,0.5)]',
    Icon: ShieldX,
  },
  high: {
    label: 'High Risk',
    sub: 'Contains concerning clauses worth reviewing',
    text: 'text-red-400',
    ring: 'border-red-500/40',
    glow: 'shadow-[0_0_34px_-8px_rgba(239,68,68,0.45)]',
    Icon: ShieldAlert,
  },
  medium: {
    label: 'Medium Risk',
    sub: 'Some clauses require your attention',
    text: 'text-amber-400',
    ring: 'border-amber-500/40',
    glow: 'shadow-[0_0_34px_-8px_rgba(245,158,11,0.4)]',
    Icon: Shield,
  },
  low: {
    label: 'Low Risk',
    sub: 'Terms appear largely standard and fair',
    text: 'text-emerald-400',
    ring: 'border-emerald-500/40',
    glow: 'shadow-[0_0_34px_-8px_rgba(16,185,129,0.4)]',
    Icon: ShieldCheck,
  },
};

export const RiskSummaryHeader = ({
  riskLevel,
  riskScore,
  isAnalyzing,
  anomalies,
  missingProtectionsCount = 0,
}: RiskSummaryHeaderProps) => {
  // Defensive lookup: a backend risk_level outside the known set (e.g. "Unknown"
  // written on the analysis-failed path) would otherwise make `meta` undefined and
  // crash the whole DocumentPage on `const { Icon } = meta`. Fall back to "low".
  const meta = RISK_META[riskLevel] ?? RISK_META.low;
  const { Icon } = meta;

  const segments: SeveritySegment[] = [
    {
      key: 'critical',
      label: 'Critical',
      count: anomalies.filter((a) => a.severity === 'critical').length,
      text: 'text-purple-400',
      bar: 'bg-purple-500',
      chipBg: 'bg-purple-500/10',
      chipBorder: 'border-purple-500/25',
      dot: 'bg-purple-500',
    },
    {
      key: 'high',
      label: 'High',
      count: anomalies.filter((a) => a.severity === 'high').length,
      text: 'text-red-400',
      bar: 'bg-red-500',
      chipBg: 'bg-red-500/10',
      chipBorder: 'border-red-500/25',
      dot: 'bg-red-500',
    },
    {
      key: 'medium',
      label: 'Medium',
      count: anomalies.filter((a) => a.severity === 'medium').length,
      text: 'text-amber-400',
      bar: 'bg-amber-500',
      chipBg: 'bg-amber-500/10',
      chipBorder: 'border-amber-500/25',
      dot: 'bg-amber-500',
    },
    {
      key: 'low',
      label: 'Low',
      count: anomalies.filter((a) => a.severity === 'low').length,
      text: 'text-emerald-400',
      bar: 'bg-emerald-500',
      chipBg: 'bg-emerald-500/10',
      chipBorder: 'border-emerald-500/25',
      dot: 'bg-emerald-500',
    },
  ];

  const totalFindings = anomalies.length;
  const totalFlags = anomalies.reduce(
    (sum, a) => sum + (a.risk_flags?.length || 0),
    0
  );

  // Normalised score for the gauge arc (0–10 → 0–100%).
  const scorePct =
    riskScore != null ? Math.max(0, Math.min(100, (riskScore / 10) * 100)) : 0;

  const hasDistribution = totalFindings > 0;

  return (
    <section
      className={`relative overflow-hidden rounded-2xl border ${meta.ring} ${meta.glow} bg-card/60 backdrop-blur-sm`}
    >
      {/* subtle grid + top accent line */}
      <div className="absolute inset-0 grid-pattern opacity-[0.04] pointer-events-none" />
      <div
        className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent ${
          isAnalyzing ? 'via-primary/50' : 'via-current'
        } to-transparent ${meta.text}`}
      />

      <div className="relative p-5 lg:p-7">
        {/* Kicker */}
        <div className="flex items-center justify-between gap-3 mb-5 lg:mb-6">
          <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em]">
            <Gauge className="h-3 w-3" />
            <span>Risk Verdict</span>
          </div>
          {!isAnalyzing && (
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Analysis complete
            </span>
          )}
        </div>

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 lg:gap-8">
          {/* Verdict + score gauge */}
          <div className="flex items-center gap-4 lg:gap-5">
            {/* Radial score gauge */}
            <div className="relative shrink-0">
              <div
                className={`h-[72px] w-[72px] lg:h-[88px] lg:w-[88px] rounded-full grid place-items-center ${meta.text} ${
                  isAnalyzing ? 'animate-pulse' : ''
                }`}
                style={
                  isAnalyzing || riskScore == null
                    ? undefined
                    : {
                        background: `conic-gradient(currentColor ${scorePct}%, hsl(var(--muted)) ${scorePct}%)`,
                      }
                }
              >
                <div className="h-[58px] w-[58px] lg:h-[72px] lg:w-[72px] rounded-full bg-background grid place-items-center">
                  {isAnalyzing ? (
                    <Loader2 className={`h-6 w-6 lg:h-7 lg:w-7 ${meta.text} animate-spin`} />
                  ) : riskScore != null ? (
                    <div className="text-center leading-none">
                      <div className={`font-data font-bold text-lg lg:text-2xl ${meta.text}`}>
                        {riskScore.toFixed(1)}
                      </div>
                      <div className="font-mono text-[8px] lg:text-[9px] text-muted-foreground tracking-wider">
                        / 10
                      </div>
                    </div>
                  ) : (
                    <Icon className={`h-6 w-6 lg:h-7 lg:w-7 ${meta.text}`} />
                  )}
                </div>
              </div>
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Icon className={`h-5 w-5 lg:h-6 lg:w-6 ${meta.text} ${isAnalyzing ? 'animate-spin' : ''}`} />
                <h2 className={`font-display font-bold text-2xl lg:text-[2rem] leading-none ${meta.text}`}>
                  {meta.label}
                </h2>
              </div>
              <p className="text-xs lg:text-sm text-muted-foreground mt-2">
                {isAnalyzing
                  ? meta.sub
                  : `${meta.sub} · based on ${totalFindings} ${
                      totalFindings === 1 ? 'finding' : 'findings'
                    }`}
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="flex items-stretch gap-0 rounded-xl border border-border/50 bg-background/40 divide-x divide-border/40 overflow-hidden">
            <Stat label="Findings" value={isAnalyzing ? '—' : totalFindings} />
            <Stat label="Risk Flags" value={isAnalyzing ? '—' : totalFlags} />
            <Stat
              label="Missing"
              value={isAnalyzing ? '—' : missingProtectionsCount}
              accent={!isAnalyzing && missingProtectionsCount > 0 ? 'text-amber-400' : undefined}
              icon={<ShieldX className="h-3 w-3" />}
            />
          </div>
        </div>

        {/* Severity distribution */}
        <div className="mt-6 lg:mt-7">
          <div className="flex items-center gap-2 mb-2.5 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em]">
            <ListChecks className="h-3 w-3" />
            <span>Severity Distribution</span>
          </div>

          {/* Segmented bar */}
          <div className="h-2.5 w-full rounded-full overflow-hidden bg-muted/60 flex">
            {isAnalyzing || !hasDistribution ? (
              <div className="h-full w-full shimmer rounded-full" />
            ) : (
              segments.map((s) =>
                s.count > 0 ? (
                  <div
                    key={s.key}
                    className={`h-full ${s.bar} transition-all duration-500`}
                    style={{ width: `${(s.count / totalFindings) * 100}%` }}
                    title={`${s.label}: ${s.count}`}
                  />
                ) : null
              )
            )}
          </div>

          {/* Severity chips */}
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {segments.map((s) => (
              <div
                key={s.key}
                className={`flex items-center justify-between rounded-lg border ${s.chipBorder} ${s.chipBg} px-2.5 py-2`}
              >
                <span className="flex items-center gap-1.5 text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                  {s.label}
                </span>
                <span className={`font-data font-bold text-sm lg:text-base ${s.count > 0 ? s.text : 'text-muted-foreground/50'}`}>
                  {isAnalyzing ? '—' : s.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

const Stat = ({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: string | number;
  accent?: string;
  icon?: React.ReactNode;
}) => (
  <div className="px-4 lg:px-5 py-3 text-center min-w-[72px] lg:min-w-[88px]">
    <div className={`font-data font-bold text-lg lg:text-2xl ${accent ?? 'text-foreground'}`}>
      {value}
    </div>
    <div className="mt-1 flex items-center justify-center gap-1 text-[9px] lg:text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
      {icon}
      {label}
    </div>
  </div>
);
