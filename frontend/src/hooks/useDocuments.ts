import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { toast } from 'sonner';

export const useDocuments = () => {
  return useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      // Fetch a generous page so the dashboard list AND its summary stats aren't
      // silently capped at the API's default page size of 10.
      const response = await api.getDocuments(0, 100);
      return response.documents; // Unwrap to get array
    },
  });
};

export const useDocument = (id: string) => {
  const query = useQuery({
    queryKey: ['documents', id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
    retry: 2,
    // Poll every 3 seconds while the document is still processing.
    refetchInterval: (query) => {
      const status = query.state.data?.processing_status;
      const analyzing =
        status === 'analyzing_anomalies' ||
        status === 'processing' ||
        status === 'embedding_completed';
      const polls = query.state.dataUpdateCount + query.state.errorUpdateCount;

      // Hard cap: a backend task that dies WITHOUT updating status leaves it stuck
      // at "analyzing_anomalies"; without a ceiling the client would poll forever.
      if (analyzing && polls < 60) return 3000; // ~3 min ceiling
      // No data yet — initial load, or a transient fetch error right after upload
      // navigation. Keep retrying briefly instead of giving up polling permanently.
      if (status === undefined && polls < 5) return 3000;
      return false; // Stop once completed/failed (or the ceiling is hit).
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
    onError: (error: unknown) => {
      const e = error as { message?: string; response?: { data?: { detail?: string } } };
      const message = e?.message || e?.response?.data?.detail || 'Failed to upload document';
      toast.error(message);
    },
  });
};

export const useUploadText = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ text, title }: { text: string; title?: string }) => api.uploadText(text, title),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Text uploaded and analyzed successfully!');
      return data;
    },
    onError: (error: unknown) => {
      const e = error as { message?: string; response?: { data?: { detail?: string } } };
      const message = e?.message || e?.response?.data?.detail || 'Failed to analyze text';
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
    onError: (error: unknown) => {
      const e = error as { message?: string; response?: { data?: { detail?: string } } };
      const message = e?.message || e?.response?.data?.detail || 'Failed to delete document';
      toast.error(message);
    },
  });
};
