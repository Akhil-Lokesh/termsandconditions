import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export const useAnomalies = (documentId: string, documentStatus?: string) => {
  return useQuery({
    queryKey: ['anomalies', documentId],
    queryFn: async () => {
      const response = await api.getAnomalies(documentId);
      return response.anomalies; // Unwrap to get array
    },
    enabled: !!documentId,
    // Poll every 3 seconds while document is still processing anomalies
    refetchInterval: () => {
      if (documentStatus === 'analyzing_anomalies' || documentStatus === 'processing' || documentStatus === 'embedding_completed') {
        return 3000; // 3 seconds
      }
      return false; // Stop polling once completed or failed
    },
  });
};
