import { useDocuments } from '@/hooks/useDocuments';
import { DocumentList } from '@/components/document/DocumentList';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Upload, FileText, AlertTriangle, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DashboardPage() {
  const { data: documents, isLoading, error } = useDocuments();

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
        <AlertDescription>Failed to load documents. Please try again.</AlertDescription>
      </Alert>
    );
  }

  const totalAnomalies = documents?.reduce((sum, doc) => sum + (doc.anomaly_count || 0), 0) || 0;
  const highRiskDocs = documents?.filter((doc) => (doc.anomaly_count || 0) > 5).length || 0;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Manage and analyze your T&C documents</p>
        </div>
        <Button asChild>
          <Link to="/upload">
            <Upload className="mr-2 h-4 w-4" />
            Upload Document
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{documents?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Analyzed documents</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Anomalies</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAnomalies}</div>
            <p className="text-xs text-muted-foreground">Detected issues</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High Risk</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{highRiskDocs}</div>
            <p className="text-xs text-muted-foreground">Documents with 5+ issues</p>
          </CardContent>
        </Card>
      </div>

      {/* Documents List */}
      {documents && documents.length > 0 ? (
        <DocumentList documents={documents} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>No Documents Yet</CardTitle>
            <CardDescription>Upload your first T&C document to get started</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Upload Document
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
