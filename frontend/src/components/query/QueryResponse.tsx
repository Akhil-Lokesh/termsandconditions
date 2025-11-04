import { QueryResponse as QueryResponseType } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CitationCard } from './CitationCard';
import { CheckCircle, MessageSquareText } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface QueryResponseProps {
  response: QueryResponseType;
}

export const QueryResponse = ({ response }: QueryResponseProps) => {
  return (
    <div className="space-y-6">
      {/* Question */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquareText className="h-5 w-5 text-primary" />
                <span className="text-sm text-muted-foreground">Your Question</span>
              </div>
              <CardTitle className="text-lg">{response.question}</CardTitle>
            </div>
            <Badge variant="secondary" className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              {formatPercentage(response.confidence)} confident
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900 leading-relaxed">{response.answer}</p>
          </div>
        </CardContent>
      </Card>

      {/* Citations */}
      {response.citations && response.citations.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">
            Sources ({response.citations.length})
          </h3>
          <div className="space-y-4">
            {response.citations.map((citation) => (
              <CitationCard key={citation.index} citation={citation} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
