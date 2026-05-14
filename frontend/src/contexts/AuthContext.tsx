import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { User, LoginRequest, SignupRequest } from '@/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    // Check if user is already logged in
    const checkAuth = async () => {
      const token = api.getToken();
      if (token) {
        try {
          const currentUser = await api.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          // Token invalid, clear it
          api.clearToken();
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const logout = useCallback(() => {
    queryClient.clear();
    api.logout();
    setUser(null);
  }, [queryClient]);

  // React to 401 responses dispatched by the API interceptor
  useEffect(() => {
    window.addEventListener('auth:logout', logout);
    return () => window.removeEventListener('auth:logout', logout);
  }, [logout]);

  const login = async (data: LoginRequest) => {
    await api.login(data);
    // After login, fetch user data
    const currentUser = await api.getCurrentUser();
    setUser(currentUser);
  };

  const signup = async (data: SignupRequest) => {
    const newUser = await api.signup(data);
    setUser(newUser);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
