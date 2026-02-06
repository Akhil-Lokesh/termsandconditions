import { Document } from '@/types';
import { DocumentCard } from './DocumentCard';

interface DocumentListProps {
  documents: Document[];
}

export const DocumentList = ({ documents }: DocumentListProps) => {
  return (
    <div className="grid gap-3 lg:gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {documents.map((document, index) => (
        <div
          key={document.id}
          className="animate-slide-up opacity-0"
          style={{
            animationDelay: `${index * 0.05}s`,
            animationFillMode: 'forwards'
          }}
        >
          <DocumentCard document={document} />
        </div>
      ))}
    </div>
  );
};
