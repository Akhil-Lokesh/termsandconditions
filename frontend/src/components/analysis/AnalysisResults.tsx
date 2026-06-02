import { Document, Anomaly, CompetitiveBenchmark } from '@/types';
import { MetadataPanel } from './MetadataPanel';
import { CompetitiveComparison } from './CompetitiveComparison';
import { RiskSummaryHeader } from './RiskSummaryHeader';
import {
  FileText,
  Loader2,
  AlertTriangle,
  Layers,
  Activity
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

  // Use backend risk_level if available, otherwise fall back to simple calculation
  const getDocumentRiskLevel = (): 'analyzing' | 'critical' | 'high' | 'medium' | 'low' => {
    if (isAnalyzing) return 'analyzing';

    // Prefer backend-calculated risk level — but ONLY if it's a known value.
    // The analysis-failed path writes risk_level="Unknown", which is not a valid
    // RiskLevel; passing it through used to crash RiskSummaryHeader. Whitelist,
    // then fall through to the anomaly-count heuristic for anything unexpected.
    const lvl = document.risk_level?.toLowerCase();
    if (lvl === 'critical' || lvl === 'high' || lvl === 'medium' || lvl === 'low') {
      return lvl;
    }

    // Fallback to simple calculation
    if (criticalSeverity > 0) return 'critical';
    if (highSeverity > 0) return 'high';
    if (mediumSeverity > 2) return 'medium';
    return 'low';
  };

  const riskLevel = getDocumentRiskLevel();

  // Missing-protection count is reliably available only through the
  // competitive benchmark payload (the per-anomaly list endpoint does not
  // expose detection_source). Surface it in the verdict header when present.
  const missingProtectionsCount = competitiveBenchmark?.missing_protections?.length ?? 0;

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Scannable risk verdict */}
      <div className="animate-slide-up">
        <RiskSummaryHeader
          riskLevel={riskLevel}
          riskScore={document.risk_score}
          isAnalyzing={isAnalyzing}
          anomalies={anomalies}
          missingProtectionsCount={missingProtectionsCount}
        />
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

      {/* Competitive Benchmark (renders its own section header internally) */}
      {competitiveBenchmark && !isAnalyzing && (
        <div className="mt-4 lg:mt-6">
          <CompetitiveComparison
            benchmark={competitiveBenchmark}
            documentRiskScore={document.risk_score ?? undefined}
          />
        </div>
      )}
    </div>
  );
};
