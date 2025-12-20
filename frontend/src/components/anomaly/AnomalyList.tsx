import { useAnomalies } from '@/hooks/useAnomalies';
import { AnomalyCard } from './AnomalyCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, CheckCircle, Clock } from 'lucide-react';

interface AnomalyListProps {
  documentId: string;
  processingStatus?: string;
}

export const AnomalyList = ({ documentId, processingStatus }: AnomalyListProps) => {
  const { data: anomalies, isLoading, error } = useAnomalies(documentId, processingStatus);

  // Check if still analyzing
  const isAnalyzing = processingStatus === 'analyzing_anomalies' ||
                      processingStatus === 'processing' ||
                      processingStatus === 'embedding_completed';

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Failed to load anomalies. Please try again.</AlertDescription>
      </Alert>
    );
  }

  if (!anomalies || anomalies.length === 0) {
    // Show different message if still analyzing
    if (isAnalyzing) {
      return (
        <Alert className="bg-blue-50 border-blue-200">
          <Clock className="h-4 w-4 text-blue-600 animate-pulse" />
          <AlertDescription className="text-blue-800">
            Analyzing document for risky clauses... Results will appear here shortly.
          </AlertDescription>
        </Alert>
      );
    }
    return (
      <Alert className="bg-green-50 border-green-200">
        <CheckCircle className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800">
          No anomalies detected! This document appears to have standard, fair terms and
          conditions.
        </AlertDescription>
      </Alert>
    );
  }

  const highSeverity = anomalies.filter((a) => a.severity === 'high');
  const mediumSeverity = anomalies.filter((a) => a.severity === 'medium');
  const lowSeverity = anomalies.filter((a) => a.severity === 'low');

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Detected Anomalies</h2>
        <p className="text-muted-foreground">
          Found {anomalies.length} potential {anomalies.length === 1 ? 'issue' : 'issues'} in
          this document
        </p>
      </div>

      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-4 max-w-2xl">
          <TabsTrigger value="all">All ({anomalies.length})</TabsTrigger>
          <TabsTrigger value="high">High ({highSeverity.length})</TabsTrigger>
          <TabsTrigger value="medium">Medium ({mediumSeverity.length})</TabsTrigger>
          <TabsTrigger value="low">Low ({lowSeverity.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4 mt-6">
          {anomalies.map((anomaly) => (
            <AnomalyCard key={anomaly.id} anomaly={anomaly} />
          ))}
        </TabsContent>

        <TabsContent value="high" className="space-y-4 mt-6">
          {highSeverity.length > 0 ? (
            highSeverity.map((anomaly) => <AnomalyCard key={anomaly.id} anomaly={anomaly} />)
          ) : (
            <Alert>
              <AlertDescription>No high severity anomalies found.</AlertDescription>
            </Alert>
          )}
        </TabsContent>

        <TabsContent value="medium" className="space-y-4 mt-6">
          {mediumSeverity.length > 0 ? (
            mediumSeverity.map((anomaly) => <AnomalyCard key={anomaly.id} anomaly={anomaly} />)
          ) : (
            <Alert>
              <AlertDescription>No medium severity anomalies found.</AlertDescription>
            </Alert>
          )}
        </TabsContent>

        <TabsContent value="low" className="space-y-4 mt-6">
          {lowSeverity.length > 0 ? (
            lowSeverity.map((anomaly) => <AnomalyCard key={anomaly.id} anomaly={anomaly} />)
          ) : (
            <Alert>
              <AlertDescription>No low severity anomalies found.</AlertDescription>
            </Alert>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};
