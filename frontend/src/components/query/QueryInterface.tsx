import { useState } from 'react';
import { useDocumentQuery } from '@/hooks/useQuery';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { QueryResponse } from './QueryResponse';
import { Loader2, Send, MessageSquare } from 'lucide-react';

interface QueryInterfaceProps {
  documentId: string;
}

const EXAMPLE_QUESTIONS = [
  'What is the refund policy?',
  'Can the company change these terms at any time?',
  'What happens to my data if I delete my account?',
  'Am I liable for any damages?',
];

export const QueryInterface = ({ documentId }: QueryInterfaceProps) => {
  const [question, setQuestion] = useState('');
  const queryMutation = useDocumentQuery();

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
            <p className="text-sm font-medium mb-3">Try these example questions:</p>
            <div className="grid gap-2">
              {EXAMPLE_QUESTIONS.map((example) => (
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
