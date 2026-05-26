import { useState, useMemo } from 'react';
import { useDocumentQuery } from '@/hooks/useQuery';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { QueryResponse } from './QueryResponse';
import { Loader2, Send, MessageSquare, Sparkles } from 'lucide-react';
import { Document, Anomaly } from '@/types';

interface QueryInterfaceProps {
  documentId: string;
  document?: Document;
  anomalies?: Anomaly[];
}

const generateExampleQuestions = (document?: Document, anomalies?: Anomaly[]): string[] => {
  const questions: string[] = [];
  const companyName = document?.metadata?.company_name || document?.metadata?.company || 'the company';

  questions.push(`What rights does ${companyName} have over my content?`);
  questions.push(`Can ${companyName} terminate my account without reason?`);

  if (anomalies && anomalies.length > 0) {
    const riskFlags = new Set<string>();
    anomalies.forEach(a => {
      a.risk_flags?.forEach(flag => riskFlags.add(flag.toLowerCase()));
    });

    if (riskFlags.has('unilateral termination') || riskFlags.has('unilateral_termination')) {
      questions.push(`Under what conditions can ${companyName} terminate my account?`);
    }
    if (riskFlags.has('content moderation control') || riskFlags.has('content_moderation')) {
      questions.push(`What content can ${companyName} remove and why?`);
    }
    if (riskFlags.has('broad usage rights') || riskFlags.has('broad_usage_rights')) {
      questions.push(`What can ${companyName} do with my uploaded content?`);
    }
    if (riskFlags.has('unlimited liability') || riskFlags.has('unlimited_liability')) {
      questions.push(`What am I liable for when using this service?`);
    }
    if (riskFlags.has('unilateral changes') || riskFlags.has('unilateral_changes')) {
      questions.push(`How will I be notified if these terms change?`);
    }
    if (riskFlags.has('broad liability disclaimer') || riskFlags.has('liability_disclaimer')) {
      questions.push(`What is ${companyName} NOT responsible for?`);
    }
    if (riskFlags.has('data collection') || riskFlags.has('data_collection')) {
      questions.push(`What personal data does ${companyName} collect?`);
    }
  }

  questions.push(`What happens to my data if I delete my account?`);
  questions.push(`Is there a dispute resolution or arbitration clause?`);

  return [...new Set(questions)].slice(0, 5);
};

export const QueryInterface = ({ documentId, document, anomalies }: QueryInterfaceProps) => {
  const [question, setQuestion] = useState('');
  const queryMutation = useDocumentQuery();

  const exampleQuestions = useMemo(
    () => generateExampleQuestions(document, anomalies),
    [document, anomalies]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      queryMutation.mutate({ document_id: documentId, question: question.trim() });
    }
  };

  const handleExampleClick = (exampleQuestion: string) => {
    setQuestion(exampleQuestion);
    queryMutation.mutate({ document_id: documentId, question: exampleQuestion });
  };

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Query Card */}
      <div className="card-interactive rounded-xl border border-border/50 overflow-hidden">
        {/* Header */}
        <div className="p-4 lg:p-5 border-b border-border/30">
          <div className="flex items-center gap-2.5 lg:gap-3">
            <div className="p-2 lg:p-2.5 rounded-lg bg-primary/10 border border-primary/20">
              <MessageSquare className="h-4 w-4 lg:h-5 lg:w-5 text-primary" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-sm lg:text-base text-foreground">Ask Questions</h3>
              <p className="text-xs lg:text-sm text-muted-foreground">
                Get answers with citations to specific clauses
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="p-4 lg:p-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Textarea
                placeholder="What questions do you have about this document?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={3}
                className="resize-none bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 placeholder:text-muted-foreground/50"
                disabled={queryMutation.isPending}
              />
              {question.length > 0 && (
                <span className="absolute bottom-3 right-3 text-xs font-mono text-muted-foreground">
                  {question.length} chars
                </span>
              )}
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={!question.trim() || queryMutation.isPending}
                className="glow-primary bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                {queryMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Send className="mr-2 h-4 w-4" />
                    Ask Question
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>

        {/* Example Questions */}
        <div className="px-4 lg:px-5 pb-4 lg:pb-5">
          <div className="pt-3 lg:pt-4 border-t border-border/30">
            <div className="flex items-center gap-2 mb-3 lg:mb-4">
              <Sparkles className="h-3.5 w-3.5 lg:h-4 lg:w-4 text-primary" />
              <span className="text-xs lg:text-sm font-medium text-foreground">Suggested questions</span>
            </div>
            <div className="grid gap-1.5 lg:gap-2">
              {exampleQuestions.map((example, index) => (
                <button
                  key={example}
                  onClick={() => handleExampleClick(example)}
                  disabled={queryMutation.isPending}
                  className="text-left text-xs lg:text-sm p-2.5 lg:p-3 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/40 hover:border-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
                  style={{
                    animationDelay: `${index * 0.05}s`,
                  }}
                >
                  <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                    {example}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Query Response */}
      {queryMutation.data && <QueryResponse response={queryMutation.data} />}

      {queryMutation.isError && (
        <div className="card-interactive rounded-xl border border-destructive/30 bg-destructive/5 p-4 lg:p-6">
          <p className="text-xs lg:text-sm text-destructive">
            Failed to get an answer. Please try rephrasing your question.
          </p>
        </div>
      )}
    </div>
  );
};
