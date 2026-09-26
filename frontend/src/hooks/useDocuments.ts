import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services/documentService';
import { toast } from '../stores/notificationStore';

export function useDocuments() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentService.getDocuments(),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, category }: { file: File | { name: string; size: number }; category?: string }) =>
      documentService.uploadDocumentSimulated(file, category, () => {
        queryClient.invalidateQueries({ queryKey: ['documents'] });
      }),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document Uploaded', `"${doc.name}" is now processed and ready.`);
    },
    onError: () => toast.error('Document upload failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentService.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.info('Document Removed');
    },
  });

  return {
    documents: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    uploadDocument: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,
    deleteDocument: deleteMutation.mutateAsync,
  };
}
