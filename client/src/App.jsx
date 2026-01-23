import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import useStore from './store/useStore';
import { authAPI } from './services/api';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import DiscoverJobs from './pages/DiscoverJobs';
import Campaign from './pages/Campaign';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const isAuthenticated = useStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Public Route Component (redirect to dashboard if already logged in)
const PublicRoute = ({ children }) => {
  const isAuthenticated = useStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  const { theme, setTheme, logout, setUser } = useStore();
  const [authChecked, setAuthChecked] = useState(false);

  // Verify authentication with backend on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await authAPI.check();
        if (response.authenticated) {
          // Update user state with backend data
          setUser({
            user_id: response.user_id,
            email: response.email,
            name: response.name,
          });
        } else {
          // Clear local auth state if not authenticated on backend
          logout();
        }
      } catch {
        // If auth check fails, clear local state
        logout();
      } finally {
        setAuthChecked(true);
      }
    };

    checkAuth();
  }, [logout, setUser]);

  // Initialize theme on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || theme;
    setTheme(savedTheme);
  }, []);

  // Don't render routes until auth is checked
  if (!authChecked) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          }
        />

        {/* Protected routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/discover"
          element={
            <ProtectedRoute>
              <DiscoverJobs />
            </ProtectedRoute>
          }
        />
        <Route
          path="/campaigns/:campaignId"
          element={
            <ProtectedRoute>
              <Campaign />
            </ProtectedRoute>
          }
        />

        {/* Default route */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* 404 - Redirect to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>

      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: theme === 'dark' ? '#1F2937' : '#FFFFFF',
            color: theme === 'dark' ? '#F9FAFB' : '#111827',
            border: `1px solid ${theme === 'dark' ? '#374151' : '#E5E7EB'}`,
          },
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#FFFFFF',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#FFFFFF',
            },
          },
        }}
      />
    </div>
  );
}

export default App;
