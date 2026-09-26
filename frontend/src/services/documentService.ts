import type { Document } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const documentService = {
  async getDocuments(): Promise<Document[]> {
    await delay(150);
    return storage.getDocuments();
  },

  async deleteDocument(id: string): Promise<void> {
    await delay(150);
    const docs = storage.getDocuments();
    storage.setDocuments(docs.filter((d) => d.id !== id));
  },

  // Simulates uploading state progression (Uploading -> Processing -> Ready)
  async uploadDocumentSimulated(
    file: File | { name: string; size: number },
    category: string = 'General',
    onProgress?: (doc: Document) => void
  ): Promise<Document> {
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(1);
    const docId = `doc-${Date.now()}`;
    const initialDoc: Document = {
      id: docId,
      name: file.name,
      size: `${sizeInMB} MB`,
      type: 'pdf',
      pageCount: Math.floor(Math.random() * 25) + 5,
      uploadedAt: new Date().toISOString().split('T')[0],
      category: category,
      status: 'uploading',
      progress: 35,
    };

    // Store transient uploading doc
    let docs = [initialDoc, ...storage.getDocuments()];
    storage.setDocuments(docs);
    onProgress?.(initialDoc);

    // Step 1: Uploading progress
    await delay(600);
    initialDoc.progress = 85;
    initialDoc.status = 'processing';
    docs = docs.map((d) => (d.id === docId ? { ...initialDoc } : d));
    storage.setDocuments(docs);
    onProgress?.(initialDoc);

    // Step 2: Processing completed
    await delay(800);
    initialDoc.progress = 100;
    initialDoc.status = 'ready';
    docs = docs.map((d) => (d.id === docId ? { ...initialDoc } : d));
    storage.setDocuments(docs);
    onProgress?.(initialDoc);

    return initialDoc;
  },
};
