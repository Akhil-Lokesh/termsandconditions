import { LoginForm } from '@/components/auth/LoginForm';
import { Logo } from '@/components/Logo';
import { Link } from 'react-router-dom';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative">
      {/* Background */}
      <div className="fixed inset-0 grid-pattern opacity-30 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />

      {/* Logo */}
      <Link to="/" className="mb-8 relative" aria-label="T&C Analyzer — home">
        <Logo />
      </Link>

      <LoginForm />

      {/* Footer */}
      <p className="mt-8 text-xs text-muted-foreground font-mono">
        Protect yourself from unfair terms
      </p>
    </div>
  );
}
