import { UploadDocument } from '@/components/document/UploadDocument';
import { Upload, Activity } from 'lucide-react';

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6 lg:space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-muted-foreground text-xs lg:text-sm font-mono">
          <Activity className="h-3 w-3" />
          <span>UPLOAD</span>
        </div>
        <div className="flex items-center gap-3 lg:gap-4">
          <div className="relative hidden sm:block">
            <div className="absolute inset-0 bg-primary/20 blur-lg rounded-lg" />
            <div className="relative p-2.5 lg:p-3 rounded-lg bg-primary/10 border border-primary/20">
              <Upload className="h-5 w-5 lg:h-6 lg:w-6 text-primary" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-display font-bold tracking-tight text-foreground">
              Upload Document
            </h1>
            <p className="text-sm lg:text-base text-muted-foreground">
              Upload a Terms & Conditions PDF to analyze for risky clauses
            </p>
          </div>
        </div>
      </div>

      <UploadDocument />
    </div>
  );
}
