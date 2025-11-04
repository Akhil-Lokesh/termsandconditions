import { SignupForm } from '@/components/auth/SignupForm';
import { FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <Link to="/" className="flex items-center gap-2 mb-8">
        <FileText className="h-8 w-8 text-primary" />
        <span className="text-2xl font-bold">T&C Analyzer</span>
      </Link>
      <SignupForm />
    </div>
  );
}
