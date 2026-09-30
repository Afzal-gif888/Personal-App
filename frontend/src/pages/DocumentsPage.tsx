import React, { useRef, useState } from 'react';
import { Upload, FileText, Trash2, Eye, Loader2, RotateCw } from 'lucide-react';
import { useDocuments } from '../hooks/useDocuments';
import { documentService } from '../services/documentService';
import { errorMessage } from '../services/api';
import { toast } from '../stores/notificationStore';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Progress } from '../components/ui/Progress';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { Table, THead, TBody, TR, TH, TD } from '../components/ui/Table';
import { Toolbar, SearchField, FilterSelect, TableFooter } from '../components/ui/Toolbar';
import { DesktopOnly, MobileList, MobileRow } from '../components/ui/ResponsiveList';
import { formatDate } from '../utils/formatters';
import { DOCUMENT_STATUS_STYLES, documentBadgeKey, documentIsIndexing, statusStyle } from '../utils/status';
import { cn } from '../utils/cn';

const DEFAULT_CATEGORIES = ['Machine Learning', 'Database Systems', 'Operating Systems', 'Algorithm Analysis', 'General'];

// Matches the backend's allowed upload types.
const ACCEPT = '.pdf,.txt,.md,.csv,.docx,.pptx,.xlsx,.png,.jpg,.jpeg';

export const DocumentsPage: React.FC = () => {
  const { documents, uploadDocument, isUploading, deleteDocument, reindexDocument } = useDocuments();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [dragActive, setDragActive] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const categories = Array.from(new Set([...DEFAULT_CATEGORIES, ...documents.map((d) => d.category)]));

  // Files go into the subject selected in the filter, or "General" when showing all.
  const uploadFiles = async (files: FileList | null) => {
    for (const file of Array.from(files ?? [])) {
      try {
        await uploadDocument({ file, category: category === 'All' ? 'General' : category });
      } catch {
        // the hook shows the error; carry on with the remaining files
      }
    }
  };

  const openDocument = async (id: string) => {
    try {
      await documentService.openDocument(id);
    } catch (err) {
      toast.error('Could not open document', errorMessage(err));
    }
  };

  const q = search.trim().toLowerCase();
  const filtered = documents.filter(
    (d) => d.name.toLowerCase().includes(q) && (category === 'All' || d.category === category)
  );

  return (
    <Page>
      <PageHeader
        title="Documents"
        description="Lecture notes, syllabi and papers the assistant can reference when planning."
        actions={
          <Button onClick={() => fileInputRef.current?.click()} isLoading={isUploading} leftIcon={<Upload className="size-4" />}>
            Upload
          </Button>
        }
      />

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT}
        multiple
        className="hidden"
        onChange={(e) => {
          uploadFiles(e.target.files);
          e.target.value = ''; // allow picking the same file again
        }}
      />

      <button
        type="button"
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          uploadFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'w-full flex flex-col sm:flex-row items-center justify-center gap-3 px-6 py-6 rounded-xl border border-dashed text-center sm:text-left transition-colors',
          dragActive ? 'border-accent bg-accent-subtle' : 'border-line-strong bg-surface hover:bg-subtle/60'
        )}
      >
        <span className="flex items-center justify-center size-10 rounded-lg border border-line bg-surface shadow-xs text-fg-subtle">
          <Upload className="size-5" />
        </span>
        <span>
          <span className="block text-sm font-medium text-fg">
            <span className="text-accent">Click to upload</span> or drag and drop
          </span>
          <span className="block text-xs text-fg-subtle mt-0.5">PDF, Word, slides, text or images · up to 25 MB</span>
        </span>
      </button>

      <Toolbar>
        <SearchField value={search} onChange={setSearch} placeholder="Search documents" />
        <FilterSelect
          label="Subject"
          value={category}
          onChange={setCategory}
          options={[{ value: 'All', label: 'All subjects' }, ...categories.map((c) => ({ value: c, label: c }))]}
        />
      </Toolbar>

      <Card flush className="overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState bare icon={<FileText />} title="No documents" description="Upload notes or a syllabus to get started." />
        ) : (
          <>
            <MobileList>
              {filtered.map((doc) => {
                const s = statusStyle(DOCUMENT_STATUS_STYLES, documentBadgeKey(doc));
                const inFlight = doc.status === 'uploading' || doc.status === 'processing';
                return (
                  <MobileRow
                    key={doc.id}
                    leading={
                      <span className="flex items-center justify-center size-9 rounded-md bg-danger-subtle text-danger text-2xs font-semibold">PDF</span>
                    }
                    title={<span className="break-all">{doc.name}</span>}
                    subtitle={`${doc.category} · ${doc.size}${doc.pageCount ? ` · ${doc.pageCount} pages` : ''}`}
                    meta={
                      inFlight ? (
                        <div className="flex items-center gap-2 w-full">
                          <Progress value={doc.progress ?? 0} label={`${doc.name} upload progress`} />
                          <span className="text-xs text-fg-subtle tabular">{doc.progress ?? 0}%</span>
                        </div>
                      ) : (
                        <>
                          <span title={doc.indexError}>
                            <Badge variant={s.variant} dot>
                              {documentIsIndexing(doc) && <Loader2 className="size-3 animate-spin" />}
                              {s.label}
                            </Badge>
                          </span>
                          <span className="text-xs text-fg-subtle">{formatDate(doc.uploadedAt)}</span>
                        </>
                      )
                    }
                    actions={
                      <RowActions
                        label={`Actions for ${doc.name}`}
                        items={[
                          ...(doc.status === 'ready' && doc.indexStatus === 'failed'
                            ? [{ id: 'reindex', label: 'Retry indexing', icon: <RotateCw />, onClick: () => reindexDocument(doc.id) }]
                            : []),
                          { id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeletingId(doc.id) },
                        ]}
                      />
                    }
                  />
                );
              })}
            </MobileList>
            <DesktopOnly>
            <Table>
              <THead>
                <tr>
                  <TH>Name</TH>
                  <TH className="hidden md:table-cell">Subject</TH>
                  <TH className="hidden lg:table-cell text-right">Size</TH>
                  <TH className="hidden lg:table-cell text-right">Pages</TH>
                  <TH className="hidden sm:table-cell">Uploaded</TH>
                  <TH>Status</TH>
                  <TH className="w-12">
                    <span className="sr-only">Actions</span>
                  </TH>
                </tr>
              </THead>
              <TBody>
                {filtered.map((doc) => {
                  const s = statusStyle(DOCUMENT_STATUS_STYLES, documentBadgeKey(doc));
                  const inFlight = doc.status === 'uploading' || doc.status === 'processing';
                  return (
                    <TR key={doc.id}>
                      <TD className="w-full max-w-0">
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="flex items-center justify-center size-8 shrink-0 rounded-md bg-danger-subtle text-danger text-2xs font-semibold">
                            PDF
                          </span>
                          <span className="min-w-0">
                            <span className="block font-medium truncate" title={doc.name}>
                              {doc.name}
                            </span>
                            {inFlight && (
                              <span className="flex items-center gap-2 mt-1">
                                <Progress value={doc.progress ?? 0} className="w-32" label={`${doc.name} upload progress`} />
                                <span className="text-xs text-fg-subtle tabular">{doc.progress ?? 0}%</span>
                              </span>
                            )}
                          </span>
                        </div>
                      </TD>
                      <TD className="hidden md:table-cell text-fg-muted">{doc.category}</TD>
                      <TD className="hidden lg:table-cell text-right text-fg-muted tabular">{doc.size}</TD>
                      <TD className="hidden lg:table-cell text-right text-fg-muted tabular">{doc.pageCount ?? '—'}</TD>
                      <TD className="hidden sm:table-cell text-fg-muted whitespace-nowrap">{formatDate(doc.uploadedAt)}</TD>
                      <TD>
                        <span title={doc.indexError}>
                          <Badge variant={s.variant} dot>
                            {(inFlight || documentIsIndexing(doc)) && <Loader2 className="size-3 animate-spin" />}
                            {s.label}
                          </Badge>
                        </span>
                      </TD>
                      <TD>
                        <RowActions
                          label={`Actions for ${doc.name}`}
                          items={[
                            ...(doc.status === 'ready'
                              ? [{ id: 'open', label: 'Open', icon: <Eye />, onClick: () => openDocument(doc.id) }]
                              : []),
                            ...(doc.status === 'ready' && doc.indexStatus === 'failed'
                              ? [{ id: 'reindex', label: 'Retry indexing', icon: <RotateCw />, onClick: () => reindexDocument(doc.id) }]
                              : []),
                            { id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeletingId(doc.id) },
                          ]}
                        />
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
            </DesktopOnly>
            <TableFooter shown={filtered.length} total={documents.length} noun="documents" />
          </>
        )}
      </Card>

      <ConfirmDialog
        isOpen={!!deletingId}
        onClose={() => setDeletingId(null)}
        onConfirm={async () => {
          if (deletingId) {
            await deleteDocument(deletingId);
            setDeletingId(null);
          }
        }}
        title="Delete document?"
        message="The assistant will no longer be able to reference this file."
      />
    </Page>
  );
};
