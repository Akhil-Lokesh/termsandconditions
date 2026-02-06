import { Document, Anomaly, CompetitiveBenchmark } from '@/types';
import { MetadataPanel } from './MetadataPanel';
import { CompetitiveComparison } from './CompetitiveComparison';
import {
  FileText,
  TrendingUp,
  Loader2,
  Shield,
  AlertTriangle,
  Layers,
  Activity,
  BarChart3
} from 'lucide-react';

interface AnalysisResultsProps {
  document: Document;
  anomalies: Anomaly[];
  competitiveBenchmark?: CompetitiveBenchmark;
}

export const AnalysisResults = ({ document, anomalies, competitiveBenchmark }: AnalysisResultsProps) => {
  const isAnalyzing = document.processing_status === 'analyzing_anomalies' ||
                      document.processing_status === 'processing' ||
                      document.processing_status === 'embedding_completed';

  const criticalSeverity = anomalies.filter((a) => a.severity === 'critical').length;
  const highSeverity = anomalies.filter((a) => a.severity === 'high').length;
  const mediumSeverity = anomalies.filter((a) => a.severity === 'medium').length;
  const lowSeverity = anomalies.filter((a) => a.severity === 'low').length;

  // Use backend risk_level if available, otherwise fall back to simple calculation
  const getDocumentRiskLevel = (): 'analyzing' | 'critical' | 'high' | 'medium' | 'low' => {
    if (isAnalyzing) return 'analyzing';

    // Prefer backend-calculated risk level
    if (document.risk_level) {
      return document.risk_level.toLowerCase() as 'critical' | 'high' | 'medium' | 'low';
    }

    // Fallback to simple calculation
    if (criticalSeverity > 0) return 'critical';
    if (highSeverity > 0) return 'high';
    if (mediumSeverity > 2) return 'medium';
    return 'low';
  };

  const riskLevel = getDocumentRiskLevel();

  const riskConfig = {
    analyzing: {
      color: 'text-primary',
      bgColor: 'bg-primary/10 border-primary/20',
      iconBg: 'bg-primary/20',
      label: 'Analyzing...',
      description: 'Scanning clauses for risky patterns'
    },
    critical: {
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10 border-purple-500/20',
      iconBg: 'bg-purple-500/20',
      label: 'Critical Risk',
      description: 'Document contains severe risk clauses'
    },
    high: {
      color: 'text-red-500',
      bgColor: 'bg-red-500/10 border-red-500/20',
      iconBg: 'bg-red-500/20',
      label: 'High Risk',
      description: 'Document contains concerning clauses'
    },
    medium: {
      color: 'text-amber-500',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
      iconBg: 'bg-amber-500/20',
      label: 'Medium Risk',
      description: 'Some clauses require attention'
    },
    low: {
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
      iconBg: 'bg-emerald-500/20',
      label: 'Low Risk',
      description: 'Document appears mostly standard'
    }
  };

  const config = riskConfig[riskLevel];

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Overall Risk Assessment */}
      <div className={`card-interactive rounded-xl border ${config.bgColor} p-4 lg:p-6`}>
        <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-wider mb-3 lg:mb-4">
          <TrendingUp className="h-3 w-3" />
          <span>Risk Assessment</span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 lg:gap-6">
          <div className="flex items-center gap-3 lg:gap-4">
            <div className={`p-3 lg:p-4 rounded-xl ${config.iconBg}`}>
              {isAnalyzing ? (
                <Loader2 className={`h-6 w-6 lg:h-8 lg:w-8 ${config.color} animate-spin`} />
              ) : (
                <Shield className={`h-6 w-6 lg:h-8 lg:w-8 ${config.color}`} />
              )}
            </div>
            <div>
              <div className="flex items-baseline gap-2 lg:gap-3">
                <p className={`text-xl lg:text-3xl font-display font-bold ${config.color}`}>
                  {config.label}
                </p>
                {!isAnalyzing && document.risk_score != null && (
                  <span className={`text-sm lg:text-lg font-data ${config.color}`}>
                    {document.risk_score.toFixed(1)}/10
                  </span>
                )}
              </div>
              <p className="text-xs lg:text-sm text-muted-foreground mt-0.5 lg:mt-1">
                {isAnalyzing
                  ? config.description
                  : `Based on ${anomalies.length} detected anomalies`}
              </p>
            </div>
          </div>

          {/* Severity breakdown */}
          <div className="flex gap-3 lg:gap-5 pt-3 lg:pt-0 border-t lg:border-t-0 border-border/30">
            <div className="text-center flex-1 lg:flex-none">
              <p className="text-lg lg:text-2xl font-data font-bold text-purple-500">
                {isAnalyzing ? '-' : criticalSeverity}
              </p>
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mt-0.5 lg:mt-1">
                Critical
              </p>
            </div>
            <div className="w-px bg-border/50" />
            <div className="text-center flex-1 lg:flex-none">
              <p className="text-lg lg:text-2xl font-data font-bold text-red-500">
                {isAnalyzing ? '-' : highSeverity}
              </p>
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mt-0.5 lg:mt-1">
                High
              </p>
            </div>
            <div className="w-px bg-border/50" />
            <div className="text-center flex-1 lg:flex-none">
              <p className="text-lg lg:text-2xl font-data font-bold text-amber-500">
                {isAnalyzing ? '-' : mediumSeverity}
              </p>
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mt-0.5 lg:mt-1">
                Medium
              </p>
            </div>
            <div className="w-px bg-border/50" />
            <div className="text-center flex-1 lg:flex-none">
              <p className="text-lg lg:text-2xl font-data font-bold text-emerald-500">
                {isAnalyzing ? '-' : lowSeverity}
              </p>
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground mt-0.5 lg:mt-1">
                Low
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats and Metadata Grid */}
      <div className="grid md:grid-cols-2 gap-4 lg:gap-6">
        {/* Document Statistics */}
        <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-5">
          <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-wider mb-3 lg:mb-4">
            <FileText className="h-3 w-3" />
            <span>Document Statistics</span>
          </div>

          <div className="space-y-0">
            <div className="flex justify-between items-center py-2 lg:py-2.5 border-b border-border/30">
              <div className="flex items-center gap-2 lg:gap-2.5">
                <div className="p-1.5 rounded-lg bg-muted/50">
                  <Layers className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <span className="text-xs lg:text-sm text-muted-foreground">Pages</span>
              </div>
              <span className="font-data text-sm lg:text-base font-medium text-foreground">{document.page_count ?? '—'}</span>
            </div>

            <div className="flex justify-between items-center py-2 lg:py-2.5 border-b border-border/30">
              <div className="flex items-center gap-2 lg:gap-2.5">
                <div className="p-1.5 rounded-lg bg-muted/50">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <span className="text-xs lg:text-sm text-muted-foreground">Total Clauses</span>
              </div>
              <span className="font-data text-sm lg:text-base font-medium text-foreground">{document.clause_count ?? '—'}</span>
            </div>

            <div className="flex justify-between items-center py-2 lg:py-2.5 border-b border-border/30">
              <div className="flex items-center gap-2 lg:gap-2.5">
                <div className="p-1.5 rounded-lg bg-muted/50">
                  <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <span className="text-xs lg:text-sm text-muted-foreground">Anomalies Detected</span>
              </div>
              {isAnalyzing ? (
                <div className="flex items-center gap-2 text-primary">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span className="font-mono text-xs lg:text-sm">Analyzing</span>
                </div>
              ) : (
                <span className={`font-data text-sm lg:text-base font-medium ${anomalies.length > 5 ? 'text-red-500' : 'text-foreground'}`}>
                  {anomalies.length}
                </span>
              )}
            </div>

            <div className="flex justify-between items-center py-2 lg:py-2.5">
              <div className="flex items-center gap-2 lg:gap-2.5">
                <div className="p-1.5 rounded-lg bg-muted/50">
                  <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <span className="text-xs lg:text-sm text-muted-foreground">Risk Flags</span>
              </div>
              {isAnalyzing ? (
                <div className="flex items-center gap-2 text-primary">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span className="font-mono text-xs lg:text-sm">Analyzing</span>
                </div>
              ) : (
                <span className="font-data text-sm lg:text-base font-medium text-foreground">
                  {anomalies.reduce((sum, a) => sum + (a.risk_flags?.length || 0), 0)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Metadata */}
        {document.metadata && <MetadataPanel metadata={document.metadata} />}
      </div>

      {/* Competitive Benchmark */}
      {competitiveBenchmark && !isAnalyzing && (
        <div className="mt-4 lg:mt-6">
          <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-wider mb-3 lg:mb-4">
            <BarChart3 className="h-3 w-3" />
            <span>Industry Comparison</span>
          </div>
          <CompetitiveComparison
            benchmark={competitiveBenchmark}
            documentRiskScore={document.risk_score ?? undefined}
          />
        </div>
      )}
    </div>
  );
};
