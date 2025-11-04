import { Link } from 'react-router-dom';
import { Document } from '@/types';
import { useDeleteDocument } from '@/hooks/useDocuments';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FileText, Calendar, AlertTriangle, Trash2, ArrowRight } from 'lucide-react';
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
  const severityVariant = anomalyCount > 5 ? 'destructive' : anomalyCount > 0 ? 'default' : 'secondary';

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <FileText className="h-5 w-5 text-primary mt-1" />
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate">{document.filename}</CardTitle>
              <CardDescription className="flex items-center gap-2 mt-1">
                <Calendar className="h-3 w-3" />
                {formatRelativeTime(document.created_at)}
              </CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Metadata */}
        <div className="space-y-2 text-sm">
          {document.metadata.company && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Company:</span>
              <span className="font-medium">{document.metadata.company}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-muted-foreground">Pages:</span>
            <span className="font-medium">{document.page_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Clauses:</span>
            <span className="font-medium">{document.clause_count}</span>
          </div>
        </div>

        {/* Anomaly Badge */}
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          <Badge variant={severityVariant}>
            {anomalyCount} {anomalyCount === 1 ? 'anomaly' : 'anomalies'}
          </Badge>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button asChild className="flex-1">
            <Link to={`/documents/${document.id}`}>
              View Details
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="icon" disabled={deleteMutation.isPending}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Document</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete "{document.filename}"? This action cannot be
                  undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
};
