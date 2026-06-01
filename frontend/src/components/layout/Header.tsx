import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { LogOut, Upload, LayoutDashboard } from 'lucide-react';
import { Logo } from '@/components/Logo';

export const Header = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-50 border-b border-border/50 backdrop-blur-xl bg-background/80">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 h-14 lg:h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/dashboard" aria-label="T&C Analyzer — home">
          <Logo />
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-0.5 lg:gap-1">
          <Link to="/dashboard">
            <Button
              variant="ghost"
              size="sm"
              className={`
                relative px-3 lg:px-4 h-8 lg:h-9 text-sm transition-all duration-200
                ${isActive('/dashboard')
                  ? 'text-primary bg-primary/10'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }
              `}
            >
              {isActive('/dashboard') && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 lg:w-8 h-0.5 bg-primary rounded-full" />
              )}
              <LayoutDashboard className="h-4 w-4 mr-1.5 lg:mr-2" />
              <span className="hidden sm:inline">Dashboard</span>
            </Button>
          </Link>
          <Link to="/upload">
            <Button
              variant="ghost"
              size="sm"
              className={`
                relative px-3 lg:px-4 h-8 lg:h-9 text-sm transition-all duration-200
                ${isActive('/upload')
                  ? 'text-primary bg-primary/10'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }
              `}
            >
              {isActive('/upload') && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 lg:w-8 h-0.5 bg-primary rounded-full" />
              )}
              <Upload className="h-4 w-4 mr-1.5 lg:mr-2" />
              <span className="hidden sm:inline">Upload</span>
            </Button>
          </Link>
        </nav>

        {/* User section */}
        <div className="flex items-center gap-2 lg:gap-3">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-muted/30 border border-border/50">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs lg:text-sm font-mono text-muted-foreground max-w-[120px] lg:max-w-none truncate">
              {user?.email}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="h-8 lg:h-9 px-2.5 lg:px-3 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="h-4 w-4 lg:mr-2" />
            <span className="hidden lg:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  );
};
