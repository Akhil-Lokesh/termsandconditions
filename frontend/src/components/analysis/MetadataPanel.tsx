import { DocumentMetadata } from '@/types';
import { Building2, MapPin, Calendar, FileType, Database, Scale, Tag, Globe } from 'lucide-react';

interface MetadataPanelProps {
  metadata: DocumentMetadata;
}

export const MetadataPanel = ({ metadata }: MetadataPanelProps) => {
  const company = metadata?.company || metadata?.company_name;

  const metadataItems = [
    { icon: Building2, label: 'Company', value: company },
    { icon: FileType, label: 'Document Type', value: metadata?.document_type },
    { icon: MapPin, label: 'Jurisdiction', value: metadata?.jurisdiction },
    { icon: Scale, label: 'Governing Law', value: metadata?.governing_law },
    { icon: Calendar, label: 'Effective Date', value: metadata?.effective_date || metadata?.last_updated },
    { icon: Tag, label: 'Version', value: metadata?.version },
    { icon: Globe, label: 'Website', value: metadata?.website },
  ].filter(item => item.value);

  return (
    <div className="card-interactive rounded-xl border border-border/50 p-4 lg:p-5">
      <div className="flex items-center gap-2 text-muted-foreground text-[10px] lg:text-xs font-mono uppercase tracking-[0.18em] mb-3 lg:mb-4">
        <Database className="h-3 w-3" />
        <span>Document Metadata</span>
      </div>

      {metadataItems.length > 0 ? (
        <dl className="space-y-0">
          {metadataItems.map((item, index) => (
            <div
              key={item.label}
              className={`flex items-center gap-2.5 lg:gap-3 py-2 lg:py-2.5 ${
                index < metadataItems.length - 1 ? 'border-b border-border/30' : ''
              }`}
            >
              <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20 shrink-0">
                <item.icon className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <dt className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  {item.label}
                </dt>
                <dd className="font-medium text-sm lg:text-base text-foreground truncate">
                  {item.value}
                </dd>
              </div>
            </div>
          ))}
        </dl>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 lg:py-8 text-center">
          <div className="p-2.5 lg:p-3 rounded-xl bg-muted/50 mb-3 lg:mb-4">
            <Database className="h-5 w-5 lg:h-6 lg:w-6 text-muted-foreground" />
          </div>
          <p className="text-xs lg:text-sm text-muted-foreground">No metadata extracted</p>
        </div>
      )}
    </div>
  );
};
