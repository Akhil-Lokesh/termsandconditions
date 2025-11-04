import { Citation } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText, TrendingUp } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface CitationCardProps {
  citation: Citation;
}

export const CitationCard = ({ citation }: CitationCardProps) => {
  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardContent className="pt-6">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="font-mono">
                [{citation.index}]
              </Badge>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="h-4 w-4" />
                <span>
                  {citation.section}
                  {citation.clause && ` - ${citation.clause}`}
                </span>
              </div>
            </div>
            <Badge variant="outline" className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              {formatPercentage(citation.relevance_score)} relevant
            </Badge>
          </div>

          {/* Citation Text */}
          <div className="bg-gray-50 p-4 rounded-lg border">
            <p className="text-sm text-gray-700 leading-relaxed">{citation.text}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
