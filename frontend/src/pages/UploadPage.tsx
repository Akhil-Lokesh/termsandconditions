import { UploadDocument } from '@/components/document/UploadDocument';

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Upload Document</h1>
        <p className="text-muted-foreground mt-1">
          Upload a Terms & Conditions PDF to analyze for risky clauses
        </p>
      </div>
      <UploadDocument />
    </div>
  );
}
