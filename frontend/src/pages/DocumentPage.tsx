import { useParams } from 'react-router-dom';
import { useDocument } from '@/hooks/useDocuments';
import { useAnomalies } from '@/hooks/useAnomalies';
import { AnalysisResults } from '@/components/analysis/AnalysisResults';
import { AnomalyList } from '@/components/anomaly/AnomalyList';
import { QueryInterface } from '@/components/query/QueryInterface';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, FileText, AlertTriangle, MessageSquare } from 'lucide-react';

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const { data: document, isLoading: docLoading, error: docError } = useDocument(id!);
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalies(id!);

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
      <div>
        <div className="flex items-center gap-3 mb-2">
          <FileText className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold">{document.filename}</h1>
        </div>
        <p className="text-muted-foreground">
          Uploaded {new Date(document.created_at).toLocaleDateString()}
        </p>
      </div>

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
            <AnomalyList documentId={id!} />
          )}
        </TabsContent>

        <TabsContent value="qa" className="mt-6">
          <QueryInterface documentId={id!} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
