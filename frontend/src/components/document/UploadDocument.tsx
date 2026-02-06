import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUploadDocument, useUploadText } from '@/hooks/useDocuments';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, FileText, Loader2, X, Cloud, CheckCircle, ClipboardPaste } from 'lucide-react';

export const UploadDocument = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const uploadMutation = useUploadDocument();
  const uploadTextMutation = useUploadText();
  const navigate = useNavigate();

  const isUploading = uploadMutation.isPending || uploadTextMutation.isPending;

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find((file) => file.type === 'application/pdf');

    if (pdfFile) {
      setSelectedFile(pdfFile);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      setSelectedFile(files[0]);
    }
  };

  const handleUploadPDF = async () => {
    if (!selectedFile) return;

    uploadMutation.mutate(selectedFile, {
      onSuccess: (data) => {
        navigate(`/documents/${data.id}`);
      },
    });
  };

  const handleUploadText = async () => {
    if (!pastedText.trim()) return;

    uploadTextMutation.mutate(
      { text: pastedText, title: textTitle || undefined },
      {
        onSuccess: (data) => {
          navigate(`/documents/${data.id}`);
        },
      }
    );
  };

  return (
    <div className="card-interactive rounded-xl border border-border/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 lg:p-5 border-b border-border/30">
        <div className="flex items-center gap-2.5 lg:gap-3">
          <div className="p-2 lg:p-2.5 rounded-lg bg-primary/10 border border-primary/20">
            <Cloud className="h-4 w-4 lg:h-5 lg:w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-sm lg:text-base text-foreground">Upload T&C Document</h3>
            <p className="text-xs lg:text-sm text-muted-foreground">
              Upload a PDF or paste text directly
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="p-4 lg:p-5">
        <Tabs defaultValue="pdf" className="w-full">
          <TabsList className="w-full bg-muted/30 border border-border/50 p-1 mb-4">
            <TabsTrigger
              value="pdf"
              className="flex-1 flex items-center justify-center gap-1.5 lg:gap-2 text-xs lg:text-sm data-[state=active]:bg-primary/10 data-[state=active]:text-primary"
              disabled={isUploading}
            >
              <Upload className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
              <span>Upload PDF</span>
            </TabsTrigger>
            <TabsTrigger
              value="text"
              className="flex-1 flex items-center justify-center gap-1.5 lg:gap-2 text-xs lg:text-sm data-[state=active]:bg-primary/10 data-[state=active]:text-primary"
              disabled={isUploading}
            >
              <ClipboardPaste className="h-3.5 w-3.5 lg:h-4 lg:w-4" />
              <span>Paste Text</span>
            </TabsTrigger>
          </TabsList>

          {/* PDF Upload Tab */}
          <TabsContent value="pdf" className="mt-0">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`
                relative rounded-xl border-2 border-dashed p-6 lg:p-10 text-center transition-all duration-300 cursor-pointer
                ${isDragging
                  ? 'border-primary bg-primary/5 scale-[1.02]'
                  : 'border-border/50 hover:border-primary/50 hover:bg-muted/30'
                }
              `}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileSelect}
                className="hidden"
                disabled={isUploading}
              />

              {selectedFile ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-3">
                    <div className="p-2.5 rounded-xl bg-primary/10 border border-primary/20">
                      <FileText className="h-6 w-6 text-primary" />
                    </div>
                    <div className="text-left min-w-0">
                      <p className="font-display font-semibold text-sm lg:text-base text-foreground truncate max-w-[200px] lg:max-w-none">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs font-mono text-muted-foreground">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                      disabled={isUploading}
                      className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    >
                      <X className="h-5 w-5" />
                    </Button>
                  </div>
                  <div className="flex items-center justify-center gap-2 text-emerald-500">
                    <CheckCircle className="h-4 w-4" />
                    <span className="text-sm font-mono">Ready to upload</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="relative mx-auto w-14 h-14 lg:w-16 lg:h-16">
                    <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse" />
                    <div className="relative w-full h-full rounded-xl bg-muted/50 border border-border/50 flex items-center justify-center">
                      <Upload className="h-6 w-6 text-muted-foreground" />
                    </div>
                  </div>
                  <div>
                    <p className="text-sm lg:text-base font-display font-semibold text-foreground mb-1">
                      Drop your PDF here, or click to browse
                    </p>
                    <p className="text-xs lg:text-sm text-muted-foreground">
                      Only PDF files are supported (max 10MB)
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* PDF Actions */}
            {selectedFile && (
              <div className="flex flex-col sm:flex-row justify-end gap-2 mt-4 pt-4 border-t border-border/30">
                <Button
                  variant="outline"
                  onClick={() => setSelectedFile(null)}
                  disabled={isUploading}
                  className="border-border/50 hover:bg-muted/50"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUploadPDF}
                  disabled={isUploading}
                  className="glow-primary bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  {uploadMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Upload & Analyze
                    </>
                  )}
                </Button>
              </div>
            )}
          </TabsContent>

          {/* Text Paste Tab */}
          <TabsContent value="text" className="mt-0 space-y-4">
            <div>
              <Input
                placeholder="Document title (optional)"
                value={textTitle}
                onChange={(e) => setTextTitle(e.target.value)}
                disabled={isUploading}
                className="bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 text-sm"
              />
            </div>
            <div>
              <Textarea
                placeholder="Paste your Terms & Conditions text here...

Example:
TERMS OF SERVICE

1. Introduction
Welcome to our service. By using our service, you agree to these terms...

2. User Responsibilities
You are responsible for maintaining the confidentiality of your account..."
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                disabled={isUploading}
                rows={12}
                className="resize-none bg-muted/30 border-border/50 focus:border-primary/50 focus:ring-primary/20 text-sm font-mono"
              />
              <div className="flex items-center justify-between mt-2">
                <p className="text-xs text-muted-foreground">
                  Minimum 100 characters required
                </p>
                <p className={`text-xs font-mono ${pastedText.length >= 100 ? 'text-emerald-500' : 'text-muted-foreground'}`}>
                  {pastedText.length.toLocaleString()} chars
                </p>
              </div>
            </div>

            {/* Text Actions */}
            <div className="flex flex-col sm:flex-row justify-end gap-2 pt-4 border-t border-border/30">
              <Button
                variant="outline"
                onClick={() => {
                  setPastedText('');
                  setTextTitle('');
                }}
                disabled={isUploading || !pastedText}
                className="border-border/50 hover:bg-muted/50"
              >
                Clear
              </Button>
              <Button
                onClick={handleUploadText}
                disabled={isUploading || pastedText.length < 100}
                className="glow-primary bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                {uploadTextMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <ClipboardPaste className="mr-2 h-4 w-4" />
                    Analyze Text
                  </>
                )}
              </Button>
            </div>
          </TabsContent>
        </Tabs>

        {/* Processing Status */}
        {isUploading && (
          <div className="mt-4 p-4 rounded-xl bg-primary/5 border border-primary/20">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-primary/10">
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
              </div>
              <div>
                <p className="font-display font-semibold text-sm text-foreground mb-1">
                  Processing your document...
                </p>
                <p className="text-xs text-muted-foreground">
                  This may take 20-30 seconds. We're extracting text, analyzing clauses, and detecting anomalies.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
