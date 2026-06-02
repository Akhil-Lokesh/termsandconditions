import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

const ANALYZING_STATUSES = ['analyzing_anomalies', 'processing', 'embedding_completed'];

export const useAnomalies = (documentId: string, documentStatus?: string) => {
  const query = useQuery({
    queryKey: ['anomalies', documentId],
    queryFn: async () => {
      const response = await api.getAnomalies(documentId);
      return response.anomalies; // Unwrap to get array
    },
    enabled: !!documentId,
    // Poll every 3 seconds while the document is still processing anomalies.
    refetchInterval: () =>
      ANALYZING_STATUSES.includes(documentStatus ?? '') ? 3000 : false,
  });

  // When the document leaves the analyzing state, do ONE final refetch. Without
  // this, polling stops the instant the status prop flips to "completed", and the
  // displayed list is whatever the last in-progress poll returned — often 0
  // anomalies captured moments before detection finished writing them, which the
  // UI then renders as a misleading "No Risks Found".
  const prevStatus = useRef(documentStatus);
  useEffect(() => {
    const wasAnalyzing = ANALYZING_STATUSES.includes(prevStatus.current ?? '');
    const nowAnalyzing = ANALYZING_STATUSES.includes(documentStatus ?? '');
    if (wasAnalyzing && !nowAnalyzing) {
      query.refetch();
    }
    prevStatus.current = documentStatus;
  }, [documentStatus, query]);

  return query;
};
