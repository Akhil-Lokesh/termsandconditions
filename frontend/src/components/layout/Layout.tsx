import { Outlet } from 'react-router-dom';
import { Header } from './Header';

export const Layout = () => {
  return (
    <div className="min-h-screen relative">
      {/* Subtle grid pattern overlay */}
      <div className="fixed inset-0 grid-pattern opacity-30 pointer-events-none" />

      {/* Main content */}
      <div className="relative z-10">
        <Header />
        <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8 animate-in">
          <Outlet />
        </main>
      </div>

      {/* Bottom fade - reduced height */}
      <div className="fixed bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-background to-transparent pointer-events-none z-20" />
    </div>
  );
};
