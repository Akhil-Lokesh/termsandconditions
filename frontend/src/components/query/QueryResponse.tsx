import { QueryResponse as QueryResponseType } from '@/types';
import { CitationCard } from './CitationCard';
import { CheckCircle, MessageSquareText, Lightbulb, BookOpen } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface QueryResponseProps {
  response: QueryResponseType;
}

const parseAnswer = (answer: string) => {
  const shortAnswerMatch = answer.match(/\*\*Short Answer:\*\*\s*(.+?)(?=\n\n|\*\*What this means|$)/s);
  const explanationMatch = answer.match(/\*\*What this means for you:\*\*\s*(.+?)$/s);

  if (shortAnswerMatch && explanationMatch) {
    return {
      shortAnswer: shortAnswerMatch[1].trim(),
      explanation: explanationMatch[1].trim(),
      isStructured: true,
    };
  }

  return {
    shortAnswer: null,
    explanation: answer,
    isStructured: false,
  };
};

const formatWithReferences = (text: string) => {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, idx) => {
    if (/^\[\d+\]$/.test(part)) {
      return (
        <span
          key={idx}
          className="inline-flex items-center justify-center bg-primary/20 text-primary text-xs font-mono font-medium px-1.5 py-0.5 rounded mx-0.5"
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
    <div className="space-y-6 animate-slide-up">
      {/* Question & Answer Card */}
      <div className="card-interactive rounded-xl border border-border/50 overflow-hidden">
        {/* Question Header */}
        <div className="p-5 border-b border-border/30">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1">
              <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 mt-0.5">
                <MessageSquareText className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1">
                  Your Question
                </p>
                <p className="font-display font-semibold text-foreground">
                  {response.question}
                </p>
              </div>
            </div>
            {response.confidence !== undefined && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
                <span className="text-xs font-mono text-emerald-500">
                  {formatPercentage(response.confidence)} confident
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Answer Content */}
        <div className="p-5 space-y-5">
          {/* Quick Answer */}
          {isStructured && shortAnswer && (
            <div className="relative rounded-xl bg-emerald-500/5 border border-emerald-500/20 p-5">
              <div className="flex items-start gap-4">
                <div className="p-2.5 rounded-xl bg-emerald-500/10">
                  <Lightbulb className="h-5 w-5 text-emerald-500" />
                </div>
                <div className="flex-1">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-emerald-500 mb-2">
                    Quick Answer
                  </h4>
                  <p className="text-foreground leading-relaxed">
                    {formatWithReferences(shortAnswer)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Detailed Explanation */}
          <div className="relative rounded-xl bg-primary/5 border border-primary/20 p-5">
            <div className="flex items-start gap-4">
              <div className="p-2.5 rounded-xl bg-primary/10">
                <BookOpen className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <h4 className="text-xs font-mono uppercase tracking-wider text-primary mb-2">
                  {isStructured ? 'What This Means For You' : 'Answer'}
                </h4>
                <p className="text-foreground/80 leading-relaxed">
                  {formatWithReferences(explanation)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Source References */}
      {response.citations && response.citations.length > 0 && (
        <div className="card-interactive rounded-xl border border-border/50 overflow-hidden">
          <div className="p-5 border-b border-border/30">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-muted/50">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-foreground">
                  Source References
                  <span className="ml-2 px-2 py-0.5 text-xs font-mono rounded bg-muted/50">
                    {response.citations.length}
                  </span>
                </h3>
                <p className="text-sm text-muted-foreground">
                  Exact clauses used to answer your question
                </p>
              </div>
            </div>
          </div>
          <div className="p-5 space-y-4">
            {response.citations.map((citation, idx) => (
              <div
                key={citation.clause_id || citation.index || idx}
                className="animate-slide-up opacity-0"
                style={{
                  animationDelay: `${idx * 0.05}s`,
                  animationFillMode: 'forwards'
                }}
              >
                <CitationCard
                  citation={citation}
                  index={idx + 1}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
