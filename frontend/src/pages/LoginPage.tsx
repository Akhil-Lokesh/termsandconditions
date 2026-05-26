import { LoginForm } from '@/components/auth/LoginForm';
import { Shield } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative">
      {/* Background */}
      <div className="fixed inset-0 grid-pattern opacity-30 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />

      {/* Logo */}
      <Link to="/" className="flex items-center gap-3 mb-8 relative group">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-lg rounded-full group-hover:bg-primary/30 transition-colors" />
          <div className="relative bg-gradient-to-br from-primary to-accent p-2.5 rounded-lg">
            <Shield className="h-6 w-6 text-primary-foreground" />
          </div>
        </div>
        <div className="flex flex-col">
          <span className="font-display font-bold text-xl tracking-tight text-foreground">
            T&C Analyzer
          </span>
          <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground -mt-0.5">
            Contract Intelligence
          </span>
        </div>
      </Link>

      <LoginForm />

      {/* Footer */}
      <p className="mt-8 text-xs text-muted-foreground font-mono">
        Protect yourself from unfair terms
      </p>
    </div>
  );
}
