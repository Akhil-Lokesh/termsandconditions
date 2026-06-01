import { useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import { toast } from 'sonner';
import type { QueryRequest } from '@/types';

export const useDocumentQuery = () => {
  return useMutation({
    mutationFn: (data: QueryRequest) => api.queryDocument(data),
    onError: (error: unknown) => {
      // api interceptor reshapes errors to { message, detail, ... } — read `.message`.
      const message = (error as { message?: string })?.message || 'Failed to query document';
      toast.error(message);
    },
  });
};
