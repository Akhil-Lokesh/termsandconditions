import { Anomaly } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SeverityBadge } from './SeverityBadge';
import { FileText, Tag } from 'lucide-react';
import { formatPercentage } from '@/utils/formatters';

interface AnomalyCardProps {
  anomaly: Anomaly;
}

export const AnomalyCard = ({ anomaly }: AnomalyCardProps) => {
  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {anomaly.section}
                {anomaly.clause_number && ` - ${anomaly.clause_number}`}
              </span>
            </div>
            <CardTitle className="text-lg">Risk Detected</CardTitle>
          </div>
          <SeverityBadge severity={anomaly.severity} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Clause Text */}
        <div className="bg-gray-50 p-4 rounded-lg border">
          <p className="text-sm italic text-gray-700">"{anomaly.clause_text}"</p>
        </div>

        {/* Explanation */}
        <div>
          <h4 className="font-semibold text-sm mb-2">Analysis</h4>
          <p className="text-sm text-muted-foreground">{anomaly.explanation}</p>
        </div>

        {/* Risk Flags */}
        {anomaly.risk_flags && anomaly.risk_flags.length > 0 && (
          <div>
            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
              <Tag className="h-4 w-4" />
              Risk Indicators
            </h4>
            <div className="flex flex-wrap gap-2">
              {anomaly.risk_flags.map((flag) => (
                <Badge key={flag} variant="outline" className="text-xs">
                  {flag.replace(/_/g, ' ')}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Prevalence Score */}
        <div className="flex items-center justify-between text-sm pt-2 border-t">
          <span className="text-muted-foreground">Prevalence in standard T&Cs:</span>
          <span className="font-medium">
            {formatPercentage(anomaly.prevalence)}
            <span className="text-xs text-muted-foreground ml-1">
              ({anomaly.prevalence < 0.3 ? 'Rare' : anomaly.prevalence < 0.7 ? 'Uncommon' : 'Common'})
            </span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
};
