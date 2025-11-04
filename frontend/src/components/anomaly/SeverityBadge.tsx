import { Badge } from '@/components/ui/badge';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';

interface SeverityBadgeProps {
  severity: 'low' | 'medium' | 'high';
}

export const SeverityBadge = ({ severity }: SeverityBadgeProps) => {
  const config = {
    high: {
      icon: AlertTriangle,
      variant: 'destructive' as const,
      label: 'High Risk',
      className: 'bg-red-100 text-red-800 hover:bg-red-100',
    },
    medium: {
      icon: AlertCircle,
      variant: 'default' as const,
      label: 'Medium Risk',
      className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
    },
    low: {
      icon: Info,
      variant: 'secondary' as const,
      label: 'Low Risk',
      className: 'bg-blue-100 text-blue-800 hover:bg-blue-100',
    },
  };

  const { icon: Icon, variant, label, className } = config[severity];

  return (
    <Badge variant={variant} className={className}>
      <Icon className="h-3 w-3 mr-1" />
      {label}
    </Badge>
  );
};
