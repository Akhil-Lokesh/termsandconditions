import { useDocuments } from '@/hooks/useDocuments';
import { DocumentList } from '@/components/document/DocumentList';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Upload,
  FileText,
  AlertTriangle,
  Shield,
  TrendingUp,
  Activity
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DashboardPage() {
  const { data: documents, isLoading, error } = useDocuments();

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse" />
          <Loader2 className="h-8 w-8 lg:h-10 lg:w-10 animate-spin text-primary relative" />
        </div>
        <p className="text-muted-foreground font-mono text-sm">Loading documents...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="bg-destructive/10 border-destructive/30">
        <AlertDescription>Failed to load documents. Please try again.</AlertDescription>
      </Alert>
    );
  }

  const totalAnomalies = documents?.reduce((sum, doc) => sum + (doc.anomaly_count || 0), 0) || 0;
  const highRiskDocs = documents?.filter((doc) => (doc.anomaly_count || 0) > 5).length || 0;
  const totalClauses = documents?.reduce((sum, doc) => sum + (doc.clause_count || 0), 0) || 0;

  return (
    <div className="space-y-6 lg:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground text-xs lg:text-sm font-mono">
            <Activity className="h-3 w-3" />
            <span>OVERVIEW</span>
          </div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-display font-bold tracking-tight">
            Dashboard
          </h1>
          <p className="text-sm lg:text-base text-muted-foreground">
            Contract analysis and risk monitoring
          </p>
        </div>
        <Button asChild className="glow-primary bg-primary hover:bg-primary/90 text-primary-foreground w-full sm:w-auto">
          <Link to="/upload">
            <Upload className="mr-2 h-4 w-4" />
            Upload Document
          </Link>
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
        {/* Total Documents */}
        <div className="card-interactive rounded-xl p-4 lg:p-5 border border-border/50">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                Documents
              </p>
              <p className="text-2xl lg:text-3xl font-display font-bold text-foreground">
                {documents?.length || 0}
              </p>
              <p className="text-xs lg:text-sm text-muted-foreground">
                Total analyzed
              </p>
            </div>
            <div className="p-2 lg:p-2.5 rounded-lg bg-primary/10 border border-primary/20">
              <FileText className="h-4 w-4 lg:h-5 lg:w-5 text-primary" />
            </div>
          </div>
        </div>

        {/* Total Clauses */}
        <div className="card-interactive rounded-xl p-4 lg:p-5 border border-border/50">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                Clauses
              </p>
              <p className="text-2xl lg:text-3xl font-display font-bold text-foreground font-data">
                {totalClauses.toLocaleString()}
              </p>
              <p className="text-xs lg:text-sm text-muted-foreground">
                Extracted
              </p>
            </div>
            <div className="p-2 lg:p-2.5 rounded-lg bg-accent/10 border border-accent/20">
              <TrendingUp className="h-4 w-4 lg:h-5 lg:w-5 text-accent" />
            </div>
          </div>
        </div>

        {/* Total Anomalies */}
        <div className="card-interactive rounded-xl p-4 lg:p-5 border border-border/50">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                Anomalies
              </p>
              <p className="text-2xl lg:text-3xl font-display font-bold text-amber-500 font-data">
                {totalAnomalies}
              </p>
              <p className="text-xs lg:text-sm text-muted-foreground">
                Risky clauses
              </p>
            </div>
            <div className="p-2 lg:p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <AlertTriangle className="h-4 w-4 lg:h-5 lg:w-5 text-amber-500" />
            </div>
          </div>
        </div>

        {/* High Risk */}
        <div className="card-interactive rounded-xl p-4 lg:p-5 border border-border/50">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                High Risk
              </p>
              <p className={`text-2xl lg:text-3xl font-display font-bold font-data ${highRiskDocs > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                {highRiskDocs}
              </p>
              <p className="text-xs lg:text-sm text-muted-foreground">
                Flagged
              </p>
            </div>
            <div className={`p-2 lg:p-2.5 rounded-lg border ${highRiskDocs > 0 ? 'bg-red-500/10 border-red-500/20' : 'bg-emerald-500/10 border-emerald-500/20'}`}>
              <Shield className={`h-4 w-4 lg:h-5 lg:w-5 ${highRiskDocs > 0 ? 'text-red-500' : 'text-emerald-500'}`} />
            </div>
          </div>
        </div>
      </div>

      {/* Documents Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg lg:text-xl font-display font-semibold">Your Documents</h2>
            <p className="text-xs lg:text-sm text-muted-foreground">
              Click on a document to view detailed analysis
            </p>
          </div>
        </div>

        {documents && documents.length > 0 ? (
          <DocumentList documents={documents} />
        ) : (
          <div className="card-interactive rounded-xl border border-border/50 p-8 lg:p-12 text-center">
            <div className="mx-auto w-12 h-12 lg:w-16 lg:h-16 rounded-xl lg:rounded-2xl bg-muted/50 flex items-center justify-center mb-4 lg:mb-6">
              <FileText className="h-6 w-6 lg:h-8 lg:w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg lg:text-xl font-display font-semibold mb-2">No Documents Yet</h3>
            <p className="text-sm text-muted-foreground mb-4 lg:mb-6 max-w-md mx-auto">
              Upload your first Terms & Conditions document to start analyzing risky clauses.
            </p>
            <Button asChild className="glow-primary bg-primary hover:bg-primary/90 text-primary-foreground">
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Upload Your First Document
              </Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
