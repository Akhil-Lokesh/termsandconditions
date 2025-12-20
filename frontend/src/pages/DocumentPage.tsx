import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useDocument } from '@/hooks/useDocuments';
import { useAnomalies } from '@/hooks/useAnomalies';
import { AnalysisResults } from '@/components/analysis/AnalysisResults';
import { AnomalyList } from '@/components/anomaly/AnomalyList';
import { QueryInterface } from '@/components/query/QueryInterface';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Loader2, FileText, AlertTriangle, MessageSquare, Clock, RefreshCw } from 'lucide-react';
import { api } from '@/services/api';
import { toast } from 'sonner';

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const { data: document, isLoading: docLoading, error: docError } = useDocument(id!);
  // Pass document status to enable polling while anomaly detection is in progress
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalies(id!, document?.processing_status);

  // Check if anomaly detection is still in progress
  const isAnalyzing = document?.processing_status === 'analyzing_anomalies' ||
                      document?.processing_status === 'processing' ||
                      document?.processing_status === 'embedding_completed';

  const handleReanalyze = async () => {
    if (!id) return;
    setIsReanalyzing(true);
    try {
      await api.reanalyzeDocument(id);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['documents', id] });
      queryClient.invalidateQueries({ queryKey: ['anomalies', id] });
      toast.success('Document re-analyzed successfully!');
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to re-analyze document';
      toast.error(message);
    } finally {
      setIsReanalyzing(false);
    }
  };

  if (docLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (docError || !document) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Failed to load document. Please try again.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Document Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <FileText className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold">{document.filename}</h1>
          </div>
          <p className="text-muted-foreground">
            Uploaded {new Date(document.created_at).toLocaleDateString()}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleReanalyze}
          disabled={isReanalyzing || isAnalyzing}
        >
          {isReanalyzing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Re-analyzing...
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              Re-analyze
            </>
          )}
        </Button>
      </div>

      {/* Processing Indicator */}
      {isAnalyzing && (
        <Alert className="bg-blue-50 border-blue-200">
          <Clock className="h-4 w-4 text-blue-600 animate-pulse" />
          <AlertDescription className="text-blue-800">
            Analyzing document for risky clauses... This may take a minute.
          </AlertDescription>
        </Alert>
      )}

      {/* Analysis Overview */}
      <AnalysisResults document={document} anomalies={anomalies || []} />

      {/* Tabs for different views */}
      <Tabs defaultValue="anomalies" className="mt-8">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="anomalies" className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Anomalies ({anomalies?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="qa" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Q&A
          </TabsTrigger>
        </TabsList>

        <TabsContent value="anomalies" className="mt-6">
          {anomaliesLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <AnomalyList documentId={id!} processingStatus={document?.processing_status} />
          )}
        </TabsContent>

        <TabsContent value="qa" className="mt-6">
          <QueryInterface documentId={id!} document={document} anomalies={anomalies} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
