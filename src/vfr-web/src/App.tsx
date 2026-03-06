import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import QuickSetup from './pages/QuickSetup';
import Home from './pages/Home';
import Studio from './pages/Studio';
import Settings from './pages/Settings';
import Technology from './pages/Technology';
import Pricing from './pages/Pricing';
import AppLayout from './components/layout/AppLayout';
import PublicLayout from './components/layout/PublicLayout';
import { useAuthStore } from './store/authStore';

// Protected Route Wrapper - Uses AppLayout
const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <AppLayout>{children}</AppLayout>;
};

// Auth Guard (Stop authenticated users from seeing Login/Register/Home again)
const AuthGuard = ({ children }: { children: ReactNode }) => {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/studio" replace />;
  }
  return <>{children}</>;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Unauthenticated / Public Routes */}
        <Route path="/" element={<AuthGuard><PublicLayout><Home /></PublicLayout></AuthGuard>} />
        <Route path="/technology" element={<AuthGuard><PublicLayout><Technology /></PublicLayout></AuthGuard>} />
        <Route path="/pricing" element={<AuthGuard><PublicLayout><Pricing /></PublicLayout></AuthGuard>} />
        <Route path="/login" element={<AuthGuard><Login /></AuthGuard>} />
        <Route path="/register" element={<AuthGuard><Register /></AuthGuard>} />

        {/* Setup Flow (Protected, but no Layout needed usually. We use layout to get the Navbar but hide it in logic) */}
        <Route path="/setup" element={<ProtectedRoute><QuickSetup /></ProtectedRoute>} />

        {/* Protected Dashboard Routes  */}
        <Route path="/studio" element={<ProtectedRoute><Studio /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />

        {/* Redirects */}
        <Route path="/avatar" element={<Navigate to="/studio" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
