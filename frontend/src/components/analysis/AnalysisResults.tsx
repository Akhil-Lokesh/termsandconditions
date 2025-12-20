import { Document, Anomaly } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MetadataPanel } from './MetadataPanel';
import { FileText, TrendingUp, Loader2 } from 'lucide-react';

interface AnalysisResultsProps {
  document: Document;
  anomalies: Anomaly[];
}

export const AnalysisResults = ({ document, anomalies }: AnalysisResultsProps) => {
  // Check if still analyzing
  const isAnalyzing = document.processing_status === 'analyzing_anomalies' ||
                      document.processing_status === 'processing' ||
                      document.processing_status === 'embedding_completed';

  const highSeverity = anomalies.filter((a) => a.severity === 'high').length;
  const mediumSeverity = anomalies.filter((a) => a.severity === 'medium').length;
  const lowSeverity = anomalies.filter((a) => a.severity === 'low').length;

  const riskLevel = isAnalyzing ? 'analyzing' :
    highSeverity > 0 ? 'high' : mediumSeverity > 2 ? 'medium' : 'low';

  const riskColor = {
    analyzing: 'text-blue-600',
    high: 'text-red-600',
    medium: 'text-yellow-600',
    low: 'text-green-600',
  }[riskLevel];

  const riskBg = {
    analyzing: 'bg-blue-50 border-blue-200',
    high: 'bg-red-50 border-red-200',
    medium: 'bg-yellow-50 border-yellow-200',
    low: 'bg-green-50 border-green-200',
  }[riskLevel];

  return (
    <div className="space-y-6">
      {/* Overall Risk Assessment */}
      <Card className={riskBg}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className={`h-5 w-5 ${riskColor}`} />
            Overall Risk Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              {isAnalyzing ? (
                <>
                  <p className={`text-3xl font-bold ${riskColor} flex items-center gap-2`}>
                    <Loader2 className="h-6 w-6 animate-spin" />
                    Analyzing...
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Scanning clauses for risky patterns
                  </p>
                </>
              ) : (
                <>
                  <p className={`text-3xl font-bold ${riskColor} capitalize`}>{riskLevel} Risk</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Based on {anomalies.length} detected anomalies
                  </p>
                </>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-red-600">{isAnalyzing ? '-' : highSeverity}</p>
                <p className="text-xs text-muted-foreground">High</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-600">{isAnalyzing ? '-' : mediumSeverity}</p>
                <p className="text-xs text-muted-foreground">Medium</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-blue-600">{isAnalyzing ? '-' : lowSeverity}</p>
                <p className="text-xs text-muted-foreground">Low</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document Stats and Metadata */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Document Statistics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Document Statistics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Pages</span>
              <Badge variant="secondary">{document.page_count}</Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Total Clauses</span>
              <Badge variant="secondary">{document.clause_count}</Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Anomalies Detected</span>
              {isAnalyzing ? (
                <Badge variant="outline" className="text-blue-600">
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                  Analyzing
                </Badge>
              ) : (
                <Badge variant={anomalies.length > 5 ? 'destructive' : 'secondary'}>
                  {anomalies.length}
                </Badge>
              )}
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Risk Flags</span>
              {isAnalyzing ? (
                <Badge variant="outline" className="text-blue-600">
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                  Analyzing
                </Badge>
              ) : (
                <Badge variant="secondary">
                  {anomalies.reduce((sum, a) => sum + (a.risk_flags?.length || 0), 0)}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Metadata */}
        <MetadataPanel metadata={document.metadata} />
      </div>
    </div>
  );
};
