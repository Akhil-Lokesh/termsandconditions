import { DocumentMetadata } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Building2, MapPin, Calendar, FileType } from 'lucide-react';

interface MetadataPanelProps {
  metadata: DocumentMetadata;
}

export const MetadataPanel = ({ metadata }: MetadataPanelProps) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileType className="h-5 w-5" />
          Document Metadata
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {metadata.company ? (
          <div className="flex items-center gap-3">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Company</p>
              <p className="font-medium">{metadata.company}</p>
            </div>
          </div>
        ) : null}

        {metadata.jurisdiction ? (
          <div className="flex items-center gap-3">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Jurisdiction</p>
              <p className="font-medium">{metadata.jurisdiction}</p>
            </div>
          </div>
        ) : null}

        {metadata.effective_date ? (
          <div className="flex items-center gap-3">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Effective Date</p>
              <p className="font-medium">{metadata.effective_date}</p>
            </div>
          </div>
        ) : null}

        {metadata.document_type ? (
          <div className="flex items-center gap-3">
            <FileType className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Document Type</p>
              <p className="font-medium">{metadata.document_type}</p>
            </div>
          </div>
        ) : null}

        {!metadata.company &&
          !metadata.jurisdiction &&
          !metadata.effective_date &&
          !metadata.document_type && (
            <p className="text-sm text-muted-foreground">No metadata extracted</p>
          )}
      </CardContent>
    </Card>
  );
};
