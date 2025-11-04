import { useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import { toast } from 'sonner';
import type { QueryRequest } from '@/types';

export const useDocumentQuery = () => {
  return useMutation({
    mutationFn: (data: QueryRequest) => api.queryDocument(data),
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to query document';
      toast.error(message);
    },
  });
};
