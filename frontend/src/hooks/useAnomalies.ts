import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export const useAnomalies = (documentId: string) => {
  return useQuery({
    queryKey: ['anomalies', documentId],
    queryFn: async () => {
      const response = await api.getAnomalies(documentId);
      return response.anomalies; // Unwrap to get array
    },
    enabled: !!documentId,
  });
};
