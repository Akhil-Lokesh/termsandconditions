import { useState, useMemo } from 'react';
import { useDocumentQuery } from '@/hooks/useQuery';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { QueryResponse } from './QueryResponse';
import { Loader2, Send, MessageSquare } from 'lucide-react';
import { Document, Anomaly } from '@/types';

interface QueryInterfaceProps {
  documentId: string;
  document?: Document;
  anomalies?: Anomaly[];
}

// Generate dynamic questions based on document and anomalies
const generateExampleQuestions = (document?: Document, anomalies?: Anomaly[]): string[] => {
  const questions: string[] = [];
  const companyName = document?.metadata?.company_name || document?.metadata?.company || 'the company';

  // Add company-specific questions
  questions.push(`What rights does ${companyName} have over my content?`);
  questions.push(`Can ${companyName} terminate my account without reason?`);

  // Add questions based on detected anomalies
  if (anomalies && anomalies.length > 0) {
    const riskFlags = new Set<string>();
    anomalies.forEach(a => {
      a.risk_flags?.forEach(flag => riskFlags.add(flag.toLowerCase()));
    });

    // Generate questions based on detected risk categories
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

  // Add general questions
  questions.push(`What happens to my data if I delete my account?`);
  questions.push(`Is there a dispute resolution or arbitration clause?`);

  // Return unique questions, max 5
  return [...new Set(questions)].slice(0, 5);
};

export const QueryInterface = ({ documentId, document, anomalies }: QueryInterfaceProps) => {
  const [question, setQuestion] = useState('');
  const queryMutation = useDocumentQuery();

  // Generate dynamic example questions based on document and anomalies
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Ask Questions
          </CardTitle>
          <CardDescription>
            Ask any question about this document and get answers with citations to specific
            clauses
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              placeholder="What questions do you have about this document? (e.g., 'What is the refund policy?')"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
              className="resize-none"
              disabled={queryMutation.isPending}
            />

            <div className="flex justify-between items-center">
              <div className="text-sm text-muted-foreground">
                {question.length > 0 && `${question.length} characters`}
              </div>
              <Button type="submit" disabled={!question.trim() || queryMutation.isPending}>
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

          {/* Example Questions */}
          <div className="pt-4 border-t">
            <p className="text-sm font-medium mb-3">Try these questions about this document:</p>
            <div className="grid gap-2">
              {exampleQuestions.map((example) => (
                <button
                  key={example}
                  onClick={() => handleExampleClick(example)}
                  disabled={queryMutation.isPending}
                  className="text-left text-sm p-3 rounded-lg border hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Query Response */}
      {queryMutation.data && <QueryResponse response={queryMutation.data} />}

      {queryMutation.isError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-sm text-red-800">
              Failed to get an answer. Please try rephrasing your question.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
