import { Document } from '@/types';
import { DocumentCard } from './DocumentCard';

interface DocumentListProps {
  documents: Document[];
}

export const DocumentList = ({ documents }: DocumentListProps) => {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Your Documents</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {documents.map((document) => (
          <DocumentCard key={document.id} document={document} />
        ))}
      </div>
    </div>
  );
};
