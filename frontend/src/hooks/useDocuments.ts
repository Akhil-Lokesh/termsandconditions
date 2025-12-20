import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { toast } from 'sonner';

export const useDocuments = () => {
  return useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const response = await api.getDocuments();
      return response.documents; // Unwrap to get array
    },
  });
};

export const useDocument = (id: string) => {
  const query = useQuery({
    queryKey: ['documents', id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
    // Poll every 3 seconds while document is still processing
    refetchInterval: (query) => {
      const status = query.state.data?.processing_status;
      // Keep polling if still analyzing
      if (status === 'analyzing_anomalies' || status === 'processing' || status === 'embedding_completed') {
        return 3000; // 3 seconds
      }
      return false; // Stop polling once completed or failed
    },
  });
  return query;
};

export const useUploadDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => api.uploadDocument(file),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document uploaded and analyzed successfully!');
      return data;
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to upload document';
      toast.error(message);
    },
  });
};

export const useDeleteDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document deleted successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to delete document';
      toast.error(message);
    },
  });
};
