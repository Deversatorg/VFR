import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import QuickSetup from './pages/QuickSetup';
import Home from './pages/Home';
import Studio from './pages/Studio';
import Wardrobe from './pages/Wardrobe';
import Technology from './pages/Technology';
import Pricing from './pages/Pricing';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Billing from './pages/Billing';
import AdminDashboard from './pages/AdminDashboard';
import ProfileDashboard from './pages/ProfileDashboard';
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

// Admin Route Guard
const AdminProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated, role } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check for admin role (assuming 'admin' or 'superadmin' string matches what .NET returns)
  const isAdmin = role?.toLowerCase() === 'admin' || role?.toLowerCase() === 'superadmin';
  
  if (!isAdmin) {
    // Optionally trigger a toast here if we had a toast library
    console.warn("Access Denied: Admin privileges required.");
    return <Navigate to="/" replace />;
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
        <Route path="/verify-email" element={<AuthGuard><VerifyEmail /></AuthGuard>} />
        <Route path="/forgot-password" element={<AuthGuard><ForgotPassword /></AuthGuard>} />
        <Route path="/reset-password" element={<AuthGuard><ResetPassword /></AuthGuard>} />

        {/* Setup Flow (Protected, but no Layout needed usually. We use layout to get the Navbar but hide it in logic) */}
        <Route path="/setup" element={<ProtectedRoute><QuickSetup /></ProtectedRoute>} />

        {/* Protected Dashboard Routes  */}
        <Route path="/studio" element={<ProtectedRoute><Studio /></ProtectedRoute>} />
        <Route path="/wardrobe" element={<ProtectedRoute><Wardrobe /></ProtectedRoute>} />
        <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfileDashboard /></ProtectedRoute>} />
        <Route path="/settings" element={<Navigate to="/profile" replace />} />
        <Route path="/admin" element={<AdminProtectedRoute><AdminDashboard /></AdminProtectedRoute>} />

        {/* Redirects */}
        <Route path="/avatar" element={<Navigate to="/studio" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
