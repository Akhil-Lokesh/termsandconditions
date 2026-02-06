import { useAnomalies } from '@/hooks/useAnomalies';
import { AnomalyCard } from './AnomalyCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, CheckCircle, Clock, Shield, Activity } from 'lucide-react';

interface AnomalyListProps {
  documentId: string;
  processingStatus?: string;
}

export const AnomalyList = ({ documentId, processingStatus }: AnomalyListProps) => {
  const { data: anomalies, isLoading, error } = useAnomalies(documentId, processingStatus);

  const isAnalyzing = processingStatus === 'analyzing_anomalies' ||
                      processingStatus === 'processing' ||
                      processingStatus === 'embedding_completed';

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-8 lg:py-12 gap-3 lg:gap-4">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse" />
          <Loader2 className="h-6 w-6 lg:h-8 lg:w-8 animate-spin text-primary relative" />
        </div>
        <p className="text-muted-foreground font-mono text-sm">Loading anomalies...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="bg-destructive/10 border-destructive/30">
        <AlertDescription>Failed to load anomalies. Please try again.</AlertDescription>
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
                Scanning document for risky clauses... Results will appear here shortly.
              </p>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="card-interactive rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 lg:p-8">
        <div className="flex items-start gap-3 lg:gap-4">
          <div className="p-2.5 lg:p-3 rounded-xl bg-emerald-500/10">
            <CheckCircle className="h-5 w-5 lg:h-6 lg:w-6 text-emerald-500" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-sm lg:text-base text-foreground mb-1">
              No Anomalies Detected
            </h3>
            <p className="text-xs lg:text-sm text-muted-foreground">
              This document appears to have standard, fair terms and conditions.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const criticalSeverity = anomalies.filter((a) => a.severity === 'critical');
  const highSeverity = anomalies.filter((a) => a.severity === 'high');
  const mediumSeverity = anomalies.filter((a) => a.severity === 'medium');
  const lowSeverity = anomalies.filter((a) => a.severity === 'low');

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-wider">
        <Shield className="h-3 w-3" />
        <span>Detected Anomalies</span>
        <span className="ml-2 px-1.5 lg:px-2 py-0.5 rounded bg-muted/50 text-foreground">
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
            <span className="ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-mono rounded bg-muted/50">
              {anomalies.length}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="critical"
            className="flex-1 sm:flex-initial text-xs lg:text-sm data-[state=active]:bg-purple-500/10 data-[state=active]:text-purple-500"
          >
            Critical
            <span className="ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-mono rounded bg-purple-500/10 text-purple-500">
              {criticalSeverity.length}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="high"
            className="flex-1 sm:flex-initial text-xs lg:text-sm data-[state=active]:bg-red-500/10 data-[state=active]:text-red-500"
          >
            High
            <span className="ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-mono rounded bg-red-500/10 text-red-500">
              {highSeverity.length}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="medium"
            className="flex-1 sm:flex-initial text-xs lg:text-sm data-[state=active]:bg-amber-500/10 data-[state=active]:text-amber-500"
          >
            Medium
            <span className="ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-mono rounded bg-amber-500/10 text-amber-500">
              {mediumSeverity.length}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="low"
            className="flex-1 sm:flex-initial text-xs lg:text-sm data-[state=active]:bg-emerald-500/10 data-[state=active]:text-emerald-500"
          >
            Low
            <span className="ml-1.5 lg:ml-2 px-1.5 py-0.5 text-[10px] lg:text-xs font-mono rounded bg-emerald-500/10 text-emerald-500">
              {lowSeverity.length}
            </span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-3 lg:space-y-4 mt-4 lg:mt-6">
          {anomalies.map((anomaly, index) => (
            <div
              key={anomaly.id}
              className="animate-slide-up opacity-0"
              style={{
                animationDelay: `${index * 0.05}s`,
                animationFillMode: 'forwards'
              }}
            >
              <AnomalyCard anomaly={anomaly} />
            </div>
          ))}
        </TabsContent>

        <TabsContent value="critical" className="space-y-3 lg:space-y-4 mt-4 lg:mt-6">
          {criticalSeverity.length > 0 ? (
            criticalSeverity.map((anomaly, index) => (
              <div
                key={anomaly.id}
                className="animate-slide-up opacity-0"
                style={{
                  animationDelay: `${index * 0.05}s`,
                  animationFillMode: 'forwards'
                }}
              >
                <AnomalyCard anomaly={anomaly} />
              </div>
            ))
          ) : (
            <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-6 text-center">
              <p className="text-xs lg:text-sm text-muted-foreground">No critical severity anomalies found.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="high" className="space-y-3 lg:space-y-4 mt-4 lg:mt-6">
          {highSeverity.length > 0 ? (
            highSeverity.map((anomaly, index) => (
              <div
                key={anomaly.id}
                className="animate-slide-up opacity-0"
                style={{
                  animationDelay: `${index * 0.05}s`,
                  animationFillMode: 'forwards'
                }}
              >
                <AnomalyCard anomaly={anomaly} />
              </div>
            ))
          ) : (
            <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-6 text-center">
              <p className="text-xs lg:text-sm text-muted-foreground">No high severity anomalies found.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="medium" className="space-y-3 lg:space-y-4 mt-4 lg:mt-6">
          {mediumSeverity.length > 0 ? (
            mediumSeverity.map((anomaly, index) => (
              <div
                key={anomaly.id}
                className="animate-slide-up opacity-0"
                style={{
                  animationDelay: `${index * 0.05}s`,
                  animationFillMode: 'forwards'
                }}
              >
                <AnomalyCard anomaly={anomaly} />
              </div>
            ))
          ) : (
            <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-6 text-center">
              <p className="text-xs lg:text-sm text-muted-foreground">No medium severity anomalies found.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="low" className="space-y-3 lg:space-y-4 mt-4 lg:mt-6">
          {lowSeverity.length > 0 ? (
            lowSeverity.map((anomaly, index) => (
              <div
                key={anomaly.id}
                className="animate-slide-up opacity-0"
                style={{
                  animationDelay: `${index * 0.05}s`,
                  animationFillMode: 'forwards'
                }}
              >
                <AnomalyCard anomaly={anomaly} />
              </div>
            ))
          ) : (
            <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-6 text-center">
              <p className="text-xs lg:text-sm text-muted-foreground">No low severity anomalies found.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};
