import { QueryResponse as QueryResponseType } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CitationCard } from './CitationCard';
import { CheckCircle, MessageSquareText, Lightbulb, BookOpen } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface QueryResponseProps {
  response: QueryResponseType;
}

// Parse the answer to extract short answer and explanation
const parseAnswer = (answer: string) => {
  // Try to extract structured format
  const shortAnswerMatch = answer.match(/\*\*Short Answer:\*\*\s*(.+?)(?=\n\n|\*\*What this means|$)/s);
  const explanationMatch = answer.match(/\*\*What this means for you:\*\*\s*(.+?)$/s);

  if (shortAnswerMatch && explanationMatch) {
    return {
      shortAnswer: shortAnswerMatch[1].trim(),
      explanation: explanationMatch[1].trim(),
      isStructured: true,
    };
  }

  // Fallback: return the whole answer
  return {
    shortAnswer: null,
    explanation: answer,
    isStructured: false,
  };
};

// Convert [1], [2] references to styled badges
const formatWithReferences = (text: string) => {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, idx) => {
    if (/^\[\d+\]$/.test(part)) {
      return (
        <span
          key={idx}
          className="inline-flex items-center justify-center bg-primary/10 text-primary text-xs font-medium px-1.5 py-0.5 rounded mx-0.5"
        >
          {part}
        </span>
      );
    }
    return part;
  });
};

export const QueryResponse = ({ response }: QueryResponseProps) => {
  const { shortAnswer, explanation, isStructured } = parseAnswer(response.answer);

  return (
    <div className="space-y-6">
      {/* Question Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquareText className="h-5 w-5 text-primary" />
                <span className="text-sm text-muted-foreground">Your Question</span>
              </div>
              <CardTitle className="text-lg">{response.question}</CardTitle>
            </div>
            {response.confidence !== undefined && (
              <Badge variant="secondary" className="flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {formatPercentage(response.confidence)} confident
              </Badge>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Short Answer - Prominent Display */}
          {isStructured && shortAnswer && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="bg-green-100 rounded-full p-2">
                  <Lightbulb className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-green-800 mb-1">Quick Answer</h4>
                  <p className="text-green-900 leading-relaxed">
                    {formatWithReferences(shortAnswer)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Detailed Explanation */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="bg-blue-100 rounded-full p-2">
                <BookOpen className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <h4 className="font-semibold text-blue-800 mb-1">
                  {isStructured ? 'What This Means For You' : 'Answer'}
                </h4>
                <p className="text-blue-900 leading-relaxed">
                  {formatWithReferences(explanation)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Source References */}
      {response.citations && response.citations.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              Source References ({response.citations.length})
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              These are the exact clauses from the document that were used to answer your question
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {response.citations.map((citation, idx) => (
                <CitationCard
                  key={citation.clause_id || citation.index || idx}
                  citation={citation}
                  index={idx + 1}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
