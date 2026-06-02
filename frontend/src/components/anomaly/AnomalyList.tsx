import { useAnomalies } from '@/hooks/useAnomalies';
import { AnomalyCard } from './AnomalyCard';
import { Anomaly } from '@/types';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle, Clock, Shield, Activity, AlertOctagon } from 'lucide-react';

interface AnomalyListProps {
  documentId: string;
  processingStatus?: string;
}

type Severity = Anomaly['severity'];

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low'];

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Critical Risk',
  high: 'High Risk',
  medium: 'Medium Risk',
  low: 'Low Risk',
};

const SEVERITY_TEXT: Record<Severity, string> = {
  critical: 'text-purple-400',
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-emerald-400',
};

const SEVERITY_DOT: Record<Severity, string> = {
  critical: 'bg-purple-500',
  high: 'bg-red-500',
  medium: 'bg-amber-500',
  low: 'bg-emerald-500',
};

/** Staggered, animated wrapper around a single card. */
const AnimatedCard = ({ anomaly, index }: { anomaly: Anomaly; index: number }) => (
  <div
    className="animate-slide-up opacity-0"
    style={{
      animationDelay: `${Math.min(index, 10) * 0.05}s`,
      animationFillMode: 'forwards',
    }}
  >
    <AnomalyCard anomaly={anomaly} />
  </div>
);

/** Section divider header used inside the grouped "All" view. */
const SeverityDivider = ({ severity, count }: { severity: Severity; count: number }) => (
  <div className="flex items-center gap-3 pt-1">
    <span className={`flex items-center gap-2 text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] ${SEVERITY_TEXT[severity]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[severity]} animate-pulse`} />
      {SEVERITY_LABEL[severity]}
    </span>
    <span className="font-data text-[10px] lg:text-xs text-muted-foreground">{count}</span>
    <div className="flex-1 h-px bg-gradient-to-r from-border/60 to-transparent" />
  </div>
);

const EmptyTab = ({ label }: { label: string }) => (
  <div className="rounded-xl border border-border/40 bg-card/40 p-6 lg:p-8 text-center">
    <CheckCircle className="h-5 w-5 text-emerald-500/70 mx-auto mb-2" />
    <p className="text-xs lg:text-sm text-muted-foreground">No {label} findings in this document.</p>
  </div>
);

/** Shimmer placeholder card shown while anomalies load. */
const SkeletonCard = () => (
  <div className="rounded-xl border border-border/50 border-l-[3px] border-l-border overflow-hidden">
    <div className="p-4 lg:p-5 border-b border-border/30 space-y-2.5">
      <div className="h-3 w-32 rounded shimmer" />
      <div className="h-4 w-2/3 rounded shimmer" />
    </div>
    <div className="p-4 lg:p-5 space-y-3">
      <div className="h-16 w-full rounded-lg shimmer" />
      <div className="h-3 w-full rounded shimmer" />
      <div className="h-3 w-4/5 rounded shimmer" />
    </div>
  </div>
);

export const AnomalyList = ({ documentId, processingStatus }: AnomalyListProps) => {
  const { data: anomalies, isLoading, error } = useAnomalies(documentId, processingStatus);

  const isAnalyzing =
    processingStatus === 'analyzing_anomalies' ||
    processingStatus === 'processing' ||
    processingStatus === 'embedding_completed';

  if (isLoading) {
    return (
      <div className="space-y-4 lg:space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em]">
          <Shield className="h-3 w-3" />
          <span>Loading findings…</span>
        </div>
        <div className="space-y-3 lg:space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="bg-destructive/10 border-destructive/30">
        <AlertDescription>Failed to load findings. Please try again.</AlertDescription>
      </Alert>
    );
  }

  if (!anomalies || anomalies.length === 0) {
    if (isAnalyzing) {
      return (
        <div className="card-interactive rounded-xl border border-primary/20 bg-primary/5 p-5 lg:p-8">
          <div className="flex items-start gap-3 lg:gap-4">
            <div className="p-2.5 lg:p-3 rounded-xl bg-primary/10">
              <Clock className="h-5 w-5 lg:h-6 lg:w-6 text-primary animate-pulse" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-sm lg:text-base text-foreground mb-1">
                Analysis in Progress
              </h3>
              <p className="text-xs lg:text-sm text-muted-foreground">
                Scanning the document for risky clauses. Findings will appear here as they're detected.
              </p>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="card-interactive rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 lg:p-10 text-center">
        <div className="inline-grid place-items-center p-3 lg:p-4 rounded-2xl bg-emerald-500/10 mb-3 lg:mb-4">
          <CheckCircle className="h-6 w-6 lg:h-8 lg:w-8 text-emerald-500" />
        </div>
        <h3 className="font-display font-semibold text-base lg:text-lg text-foreground mb-1.5">
          No Risks Found
        </h3>
        <p className="text-xs lg:text-sm text-muted-foreground max-w-sm mx-auto">
          This document appears to use standard, consumer-fair terms. We did not flag any risky clauses.
        </p>
      </div>
    );
  }

  // Group + order by severity (critical → low).
  const groups = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    items: anomalies.filter((a) => a.severity === sev),
  })).filter((g) => g.items.length > 0);

  const bySeverity = (sev: Severity) => anomalies.filter((a) => a.severity === sev);
  const counts: Record<Severity, number> = {
    critical: bySeverity('critical').length,
    high: bySeverity('high').length,
    medium: bySeverity('medium').length,
    low: bySeverity('low').length,
  };

  const renderTab = (sev: Severity) => {
    const items = bySeverity(sev);
    if (items.length === 0) return <EmptyTab label={SEVERITY_LABEL[sev].toLowerCase()} />;
    return (
      <div className="space-y-3 lg:space-y-4">
        {items.map((a, i) => (
          <AnimatedCard key={a.id} anomaly={a} index={i} />
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em]">
        <AlertOctagon className="h-3 w-3" />
        <span>Detected Findings</span>
        <span className="ml-1 font-data px-1.5 lg:px-2 py-0.5 rounded bg-muted/60 text-foreground">
          {anomalies.length}
        </span>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList className="bg-muted/30 border border-border/50 p-1 w-full sm:w-auto flex-wrap">
          <TabsTrigger
            value="all"
            className="flex-1 sm:flex-initial text-xs lg:text-sm data-[state=active]:bg-primary/10 data-[state=active]:text-primary"
          >
            <Activity className="h-3.5 w-3.5 lg:h-4 lg:w-4 mr-1.5 lg:mr-2" />
            All
            <span className="ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-data rounded bg-muted/50">
              {anomalies.length}
            </span>
          </TabsTrigger>
          {SEVERITY_ORDER.map((sev) => (
            <TabsTrigger
              key={sev}
              value={sev}
              className={`flex-1 sm:flex-initial text-xs lg:text-sm capitalize ${
                sev === 'critical'
                  ? 'data-[state=active]:bg-purple-500/10 data-[state=active]:text-purple-400'
                  : sev === 'high'
                  ? 'data-[state=active]:bg-red-500/10 data-[state=active]:text-red-400'
                  : sev === 'medium'
                  ? 'data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-400'
                  : 'data-[state=active]:bg-emerald-500/10 data-[state=active]:text-emerald-400'
              }`}
            >
              {sev}
              <span
                className={`ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-data rounded ${
                  sev === 'critical'
                    ? 'bg-purple-500/10 text-purple-400'
                    : sev === 'high'
                    ? 'bg-red-500/10 text-red-400'
                    : sev === 'medium'
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-emerald-500/10 text-emerald-400'
                }`}
              >
                {counts[sev]}
              </span>
            </TabsTrigger>
          ))}
        </TabsList>

        {/* All — grouped by severity with dividers */}
        <TabsContent value="all" className="mt-4 lg:mt-6 space-y-5 lg:space-y-7">
          {groups.map((group) => (
            <div key={group.severity} className="space-y-3 lg:space-y-4">
              <SeverityDivider severity={group.severity} count={group.items.length} />
              {group.items.map((a, i) => (
                <AnimatedCard key={a.id} anomaly={a} index={i} />
              ))}
            </div>
          ))}
        </TabsContent>

        {SEVERITY_ORDER.map((sev) => (
          <TabsContent key={sev} value={sev} className="mt-4 lg:mt-6">
            {renderTab(sev)}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};
