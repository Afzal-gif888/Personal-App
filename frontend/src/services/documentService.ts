import type { Document, DocumentIndexStatus, DocumentStatus } from '../types';
import { api } from './api';

interface DocumentOut {
  id: string;
  name: string;
  mimeType: string;
  size: number;
  category: string | null;
  status: DocumentStatus | 'deleted';
  pageCount: number | null;
  uploadedAt: string;
  indexStatus: DocumentIndexStatus;
  indexError: string | null;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileType(name: string, mime: string): string {
  const ext = name.includes('.') ? name.split('.').pop()!.toLowerCase() : '';
  return ext || mime.split('/').pop() || 'file';
}

const toDocument = (d: DocumentOut): Document => ({
  id: d.id,
  name: d.name,
  size: formatSize(d.size),
  type: fileType(d.name, d.mimeType),
  pageCount: d.pageCount ?? undefined,
  uploadedAt: d.uploadedAt.slice(0, 10),
  category: d.category ?? 'General',
  status: d.status === 'deleted' ? 'failed' : d.status,
  indexStatus: d.indexStatus,
  indexError: d.indexError ?? undefined,
});

export const documentService = {
  async getDocuments(): Promise<Document[]> {
    return (await api.getAll<DocumentOut>('/documents')).map(toDocument);
  },

  /** Queue the document for indexing again (e.g. after a failure). */
  async reindexDocument(id: string): Promise<Document> {
    return toDocument(await api.post<DocumentOut>(`/documents/${id}/reindex`));
  },

  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
  },

  /** Uploads the file. The server reads it, then indexes its text for search in the background. */
  async uploadDocument(file: File, category: string = 'General'): Promise<Document> {
    const form = new FormData();
    form.append('file', file);
    form.append('category', category);
    return toDocument(await api.upload<DocumentOut>('/documents', form));
  },

  /** Downloads with the auth header and opens the file in a new tab. */
  async openDocument(id: string): Promise<void> {
    // Open the tab synchronously so popup blockers allow it, then point it at the file.
    const tab = window.open('', '_blank');
    try {
      const url = URL.createObjectURL(await api.blob(`/documents/${id}/download`));
      if (tab) tab.location.href = url;
      else window.location.assign(url);
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      tab?.close();
      throw err;
    }
  },
};
