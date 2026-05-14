import { formatDistanceToNow } from 'date-fns';

export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return formatDistanceToNow(d, { addSuffix: true });
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
