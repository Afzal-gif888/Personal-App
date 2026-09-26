import React, { useState } from 'react';
import { Upload, Search, FileText, Trash2, Eye, Loader2, Filter } from 'lucide-react';
import { useDocuments } from '../hooks/useDocuments';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { formatDate } from '../utils/formatters';

export const DocumentsPage: React.FC = () => {
  const { documents, uploadDocument, isUploading, deleteDocument } = useDocuments();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [dragActive, setDragActive] = useState(false);

  const handleDemoUpload = async () => {
    const sampleFiles = [
      { name: 'CS229_Neural_Net_Optimization_Notes.pdf', size: 3450000 },
      { name: 'DBMS_Concurrency_Control_Paper.pdf', size: 1890000 },
      { name: 'OS_Kernel_Architecture_Guide.pdf', size: 4200000 },
    ];
    const picked = sampleFiles[Math.floor(Math.random() * sampleFiles.length)];
    await uploadDocument({ file: picked, category: 'Machine Learning' });
  };

  const filteredDocs = documents.filter((d) => {
    const matchesSearch = d.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || d.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6 text-left">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EAEAEA]">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-[#111111] tracking-tight">Document Library</h1>
          <p className="text-xs text-[#666666] mt-0.5">Upload syllabus PDFs, lecture slides, and notes for AI analysis</p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={handleDemoUpload}
          isLoading={isUploading}
          leftIcon={<Upload className="w-4 h-4" />}
        >
          Simulate PDF Upload
        </Button>
      </div>

      {/* Drag & Drop Upload Zone Simulation */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleDemoUpload();
        }}
        className={`p-6 rounded-lg border-2 border-dashed text-center transition-colors cursor-pointer ${
          dragActive ? 'border-black bg-[#F7F7F7]' : 'border-[#EAEAEA] bg-[#F7F7F7]/50 hover:border-[#D1D1D1]'
        }`}
        onClick={handleDemoUpload}
      >
        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="w-10 h-10 rounded-full bg-white border border-[#EAEAEA] flex items-center justify-center">
            <Upload className="w-5 h-5 text-[#666666]" />
          </div>
          <div>
            <p className="text-xs font-semibold text-[#111111]">
              Click or drag PDF documents here to upload
            </p>
            <p className="text-[11px] text-[#8A8A8A] mt-0.5">Supports PDF files up to 25MB</p>
          </div>
        </div>
      </div>

      {/* Controls Bar: Search & Category Filter */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="w-full sm:w-72">
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="w-4 h-4" />}
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-[#8A8A8A] shrink-0" />
          <Select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            options={[
              { value: 'All', label: 'All Categories' },
              { value: 'Machine Learning', label: 'Machine Learning' },
              { value: 'Database Systems', label: 'Database Systems' },
              { value: 'Operating Systems', label: 'Operating Systems' },
              { value: 'Algorithm Analysis', label: 'Algorithm Analysis' },
              { value: 'General', label: 'General' },
            ]}
          />
        </div>
      </div>

      {/* Document Grid */}
      {filteredDocs.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8 text-[#8A8A8A]" />}
          title="No documents found"
          description="Upload your lecture notes or syllabus PDFs to populate your document workspace."
          actionLabel="Upload Sample PDF"
          onAction={handleDemoUpload}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocs.map((doc) => (
            <Card key={doc.id} className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-lg bg-[#F7F7F7] border border-[#EAEAEA] text-[#111111] shrink-0">
                  <FileText className="w-6 h-6 text-[#111111]" />
                </div>

                <div className="space-y-1 flex-1 min-w-0">
                  <h3 className="text-xs sm:text-sm font-semibold text-[#111111] truncate" title={doc.name}>
                    {doc.name}
                  </h3>
                  <div className="flex items-center gap-2 text-[11px] text-[#666666]">
                    <span>{doc.size}</span>
                    <span>•</span>
                    <span>{doc.pageCount} pages</span>
                  </div>
                </div>
              </div>

              {/* Progress bar if uploading / processing */}
              {doc.status !== 'ready' ? (
                <div className="space-y-1.5 p-2 rounded bg-[#F7F7F7] border border-[#EAEAEA]">
                  <div className="flex items-center justify-between text-[10px] font-semibold text-[#111111]">
                    <span className="flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin text-black" />
                      {doc.status === 'uploading' ? 'Uploading...' : 'Processing document...'}
                    </span>
                    <span>{doc.progress}%</span>
                  </div>
                  <div className="w-full bg-[#EAEAEA] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-black h-full transition-all duration-300"
                      style={{ width: `${doc.progress}%` }}
                    />
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between text-[11px] text-[#8A8A8A] pt-1">
                  <span>Uploaded {formatDate(doc.uploadedAt)}</span>
                  <Badge variant="neutral" size="sm">
                    {doc.category}
                  </Badge>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 border-t border-[#EAEAEA]">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={doc.status !== 'ready'}
                  leftIcon={<Eye className="w-3.5 h-3.5" />}
                  className="text-xs h-7 px-3"
                >
                  Open
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteDocument(doc.id)}
                  className="p-1 text-[#8A8A8A] hover:text-red-600"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
