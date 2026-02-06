import { useParams, Link } from 'react-router-dom';
import { useDocument } from '@/hooks/useDocuments';
import { useAnomalies } from '@/hooks/useAnomalies';
import { useAnomalyReport } from '@/hooks/useAnomalyReport';
import { AnalysisResults } from '@/components/analysis/AnalysisResults';
import { AnomalyList } from '@/components/anomaly/AnomalyList';
import { QueryInterface } from '@/components/query/QueryInterface';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  FileText,
  AlertTriangle,
  MessageSquare,
  Clock,
  ArrowLeft,
  Activity
} from 'lucide-react';

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const { data: document, isLoading: docLoading, error: docError } = useDocument(id!);
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalies(id!, document?.processing_status);
  const { data: report } = useAnomalyReport(id!, document?.processing_status);

  // Show analyzing indicator
  const isAnalyzing = document?.processing_status === 'analyzing_anomalies' ||
                      document?.processing_status === 'processing' ||
                      document?.processing_status === 'embedding_completed';

  if (docLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 lg:py-24 gap-4">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse" />
          <Loader2 className="h-8 w-8 lg:h-10 lg:w-10 animate-spin text-primary relative" />
        </div>
        <p className="text-muted-foreground font-mono text-sm">Loading document...</p>
      </div>
    );
  }

  if (docError || !document) {
    return (
      <Alert variant="destructive" className="bg-destructive/10 border-destructive/30">
        <AlertDescription>Failed to load document. Please try again.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6 lg:space-y-8">
      {/* Back Button */}
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
      >
        <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </Link>

      {/* Document Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 lg:gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground text-xs lg:text-sm font-mono">
            <Activity className="h-3 w-3" />
            <span>DOCUMENT ANALYSIS</span>
          </div>
          <div className="flex items-center gap-3 lg:gap-4">
            <div className="relative hidden sm:block">
              <div className="absolute inset-0 bg-primary/20 blur-lg rounded-lg" />
              <div className="relative p-2.5 lg:p-3 rounded-lg bg-primary/10 border border-primary/20">
                <FileText className="h-5 w-5 lg:h-6 lg:w-6 text-primary" />
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-display font-bold tracking-tight text-foreground truncate">
                {document.filename}
              </h1>
              <p className="text-muted-foreground text-xs lg:text-sm font-mono">
                Uploaded {new Date(document.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric'
                })}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Processing Indicator */}
      {isAnalyzing && (
        <Alert className="bg-primary/5 border-primary/20">
          <Clock className="h-4 w-4 text-primary animate-pulse" />
          <AlertDescription className="text-foreground">
            <span className="font-medium text-primary">Analyzing in progress...</span>
            <span className="text-muted-foreground ml-2">
              Scanning clauses for risky patterns. This may take a minute.
            </span>
          </AlertDescription>
        </Alert>
      )}

      {/* Analysis Overview */}
      <AnalysisResults
        document={document}
        anomalies={anomalies || []}
        competitiveBenchmark={report?.competitive_benchmark}
      />

      {/* Tabs */}
      <Tabs defaultValue="anomalies" className="mt-6 lg:mt-8">
        <TabsList className="bg-muted/30 border border-border/50 p-1 w-full sm:w-auto">
          <TabsTrigger
            value="anomalies"
            className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 lg:gap-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 border border-transparent text-xs lg:text-sm"
          >
            <AlertTriangle className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
            <span>Anomalies</span>
            <span className="ml-1 px-1.5 py-0.5 text-xs font-mono rounded bg-muted/50">
              {anomalies?.length || 0}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="qa"
            className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 lg:gap-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 border border-transparent text-xs lg:text-sm"
          >
            <MessageSquare className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
            <span>Q&A</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="anomalies" className="mt-4 lg:mt-6">
          {anomaliesLoading ? (
            <div className="flex flex-col items-center justify-center py-8 lg:py-12 gap-4">
              <Loader2 className="h-6 w-6 lg:h-8 lg:w-8 animate-spin text-primary" />
              <p className="text-muted-foreground font-mono text-sm">Loading anomalies...</p>
            </div>
          ) : (
            <AnomalyList documentId={id!} processingStatus={document?.processing_status} />
          )}
        </TabsContent>

        <TabsContent value="qa" className="mt-4 lg:mt-6">
          <QueryInterface documentId={id!} document={document} anomalies={anomalies} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
