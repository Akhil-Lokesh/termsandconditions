import { Citation } from '@/types';
import { FileText, TrendingUp, Quote } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface CitationCardProps {
  citation: Citation;
  index?: number;
}

export const CitationCard = ({ citation, index }: CitationCardProps) => {
  const displayIndex = citation.index ?? index ?? citation.clause_id;

  return (
    <div className="rounded-xl border border-border/50 border-l-4 border-l-primary bg-muted/10 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border/30 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 text-xs font-mono font-medium rounded bg-primary/10 text-primary border border-primary/20">
            [{displayIndex}]
          </span>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            <span className="font-mono text-xs uppercase tracking-wider">
              {citation.section}
              {citation.clause && ` - ${citation.clause}`}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/50 border border-border/50">
          <TrendingUp className="h-3 w-3 text-muted-foreground" />
          <span className="text-xs font-mono text-muted-foreground">
            {formatPercentage(citation.relevance_score)} relevant
          </span>
        </div>
      </div>

      {/* Citation Text */}
      <div className="p-4">
        <div className="flex items-start gap-2 text-muted-foreground mb-2">
          <Quote className="h-3 w-3 mt-1 flex-shrink-0" />
          <span className="text-xs font-mono uppercase tracking-wider">From Document</span>
        </div>
        <p className="text-sm text-foreground/80 leading-relaxed pl-5">
          "{citation.text}"
        </p>
      </div>
    </div>
  );
};
