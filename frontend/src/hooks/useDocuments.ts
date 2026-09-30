import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services/documentService';
import { toast } from '../stores/notificationStore';
import { errorMessage } from '../services/api';

export function useDocuments() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentService.getDocuments(),
    // Indexing happens after the upload returns; poll until it settles.
    refetchInterval: (q) =>
      q.state.data?.some((d) => d.status === 'ready' && (d.indexStatus === 'pending' || d.indexStatus === 'indexing'))
        ? 3000
        : false,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, category }: { file: File; category?: string }) => documentService.uploadDocument(file, category),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      if (doc.status === 'failed') {
        toast.warning('Document Uploaded', `"${doc.name}" was saved, but its text couldn't be extracted.`);
      } else {
        toast.success('Document Uploaded', `"${doc.name}" is uploaded. Indexing it so the assistant can search it.`);
      }
    },
    onError: (err) => toast.error('Document upload failed', errorMessage(err)),
  });

  const reindexMutation = useMutation({
    mutationFn: (id: string) => documentService.reindexDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
    onError: (err) => toast.error('Could not retry indexing', errorMessage(err)),
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
    reindexDocument: reindexMutation.mutateAsync,
  };
}
