import { AlertTriangle, AlertCircle, Info, ShieldAlert } from 'lucide-react';

interface SeverityBadgeProps {
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export const SeverityBadge = ({ severity }: SeverityBadgeProps) => {
  const config = {
    critical: {
      icon: ShieldAlert,
      label: 'Critical Risk',
      className: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
      dotClass: 'bg-purple-500',
    },
    high: {
      icon: AlertTriangle,
      label: 'High Risk',
      className: 'bg-red-500/10 text-red-500 border-red-500/20',
      dotClass: 'bg-red-500',
    },
    medium: {
      icon: AlertCircle,
      label: 'Medium Risk',
      className: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
      dotClass: 'bg-amber-500',
    },
    low: {
      icon: Info,
      label: 'Low Risk',
      className: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
      dotClass: 'bg-emerald-500',
    },
  };

  // Fallback to high if severity is unknown
  const severityKey = config[severity] ? severity : 'high';
  const { icon: Icon, label, className, dotClass } = config[severityKey];

  return (
    <div
      className={`inline-flex items-center gap-1.5 lg:gap-2 px-2.5 lg:px-3 py-1 lg:py-1.5 rounded-full border ${className}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        <span className={`absolute inline-flex h-full w-full rounded-full ${dotClass} opacity-60 animate-ping`} />
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${dotClass}`} />
      </span>
      <Icon className="h-3 w-3 lg:h-3.5 lg:w-3.5" />
      <span className="text-[10px] lg:text-xs font-mono font-medium uppercase tracking-wider whitespace-nowrap">
        {label}
      </span>
    </div>
  );
};
