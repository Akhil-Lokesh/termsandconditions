import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export const useAnomalyReport = (documentId: string, documentStatus?: string) => {
  return useQuery({
    queryKey: ['anomalyReport', documentId],
    queryFn: async () => {
      const report = await api.getAnomalyReport(documentId);
      return report;
    },
    enabled: !!documentId && documentStatus === 'completed',
    // Don't refetch automatically - report is expensive to generate
    staleTime: 5 * 60 * 1000, // Consider fresh for 5 minutes
    retry: 1, // Only retry once on failure
  });
};
