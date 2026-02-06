import { Link } from 'react-router-dom';
import { Document } from '@/types';
import { useDeleteDocument } from '@/hooks/useDocuments';
import { Button } from '@/components/ui/button';
import {
  FileText,
  Calendar,
  AlertTriangle,
  Trash2,
  ArrowRight,
  Building2,
  Layers
} from 'lucide-react';
import { formatRelativeTime } from '@/utils/formatters';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

interface DocumentCardProps {
  document: Document;
}

export const DocumentCard = ({ document }: DocumentCardProps) => {
  const deleteMutation = useDeleteDocument();

  const handleDelete = () => {
    deleteMutation.mutate(document.id);
  };

  const anomalyCount = document.anomaly_count || 0;

  // Determine risk level styling
  const getRiskStyle = () => {
    if (anomalyCount > 5) {
      return {
        bgClass: 'bg-red-500/10 border-red-500/30',
        textClass: 'text-red-500',
        dotClass: 'bg-red-500',
        label: 'High Risk'
      };
    } else if (anomalyCount > 0) {
      return {
        bgClass: 'bg-amber-500/10 border-amber-500/30',
        textClass: 'text-amber-500',
        dotClass: 'bg-amber-500',
        label: 'Medium Risk'
      };
    } else {
      return {
        bgClass: 'bg-emerald-500/10 border-emerald-500/30',
        textClass: 'text-emerald-500',
        dotClass: 'bg-emerald-500',
        label: 'Low Risk'
      };
    }
  };

  const riskStyle = getRiskStyle();

  return (
    <div className="card-interactive rounded-xl border border-border/50 overflow-hidden group">
      {/* Header with risk indicator */}
      <div className="p-4 lg:p-5 pb-3 lg:pb-4">
        <div className="flex items-start gap-2.5 lg:gap-3">
          {/* Document icon with glow */}
          <div className="relative hidden sm:block">
            <div className="absolute inset-0 bg-primary/20 blur-lg rounded-lg opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative p-2 lg:p-2.5 rounded-lg bg-primary/10 border border-primary/20">
              <FileText className="h-4 w-4 lg:h-5 lg:w-5 text-primary" />
            </div>
          </div>

          {/* Title and timestamp */}
          <div className="flex-1 min-w-0">
            <h3 className="font-display font-semibold text-sm lg:text-base text-foreground truncate group-hover:text-primary transition-colors">
              {document.filename}
            </h3>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] lg:text-xs text-muted-foreground font-mono">
              <Calendar className="h-3 w-3" />
              <span>{formatRelativeTime(document.created_at)}</span>
            </div>
          </div>

          {/* Risk badge */}
          <div className={`flex items-center gap-1 lg:gap-1.5 px-2 lg:px-2.5 py-0.5 lg:py-1 rounded-full border ${riskStyle.bgClass}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${riskStyle.dotClass} animate-pulse`} />
            <span className={`text-[10px] lg:text-xs font-mono font-medium ${riskStyle.textClass}`}>
              {riskStyle.label}
            </span>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="px-4 lg:px-5 py-3 lg:py-4 border-t border-border/30 bg-muted/20">
        <div className="grid grid-cols-3 gap-3 lg:gap-4">
          {/* Company */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Building2 className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase tracking-wider">Company</span>
            </div>
            <p className="text-sm font-medium text-foreground truncate">
              {document.metadata?.company || 'Unknown'}
            </p>
          </div>

          {/* Clauses */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Layers className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase tracking-wider">Clauses</span>
            </div>
            <p className="text-sm font-data font-medium text-foreground">
              {document.clause_count || 0}
            </p>
          </div>

          {/* Anomalies */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <AlertTriangle className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase tracking-wider">Anomalies</span>
            </div>
            <p className={`text-sm font-data font-medium ${riskStyle.textClass}`}>
              {anomalyCount}
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-3 lg:p-4 border-t border-border/30 flex gap-2">
        <Button
          asChild
          className="flex-1 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 hover:border-primary/40 transition-all text-xs lg:text-sm"
          variant="ghost"
          size="sm"
        >
          <Link to={`/documents/${document.id}`} className="flex items-center justify-center">
            <span>View Analysis</span>
            <ArrowRight className="ml-2 h-3.5 w-3.5 lg:h-4 lg:w-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </Button>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              disabled={deleteMutation.isPending}
              className="h-8 w-8 lg:h-9 lg:w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10 border border-border/50 hover:border-destructive/30 transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="bg-card border-border/50">
            <AlertDialogHeader>
              <AlertDialogTitle className="font-display">Delete Document</AlertDialogTitle>
              <AlertDialogDescription className="text-muted-foreground">
                Are you sure you want to delete "{document.filename}"? This action cannot be
                undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-muted/50 border-border/50 hover:bg-muted">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
};
