import type { ReactNode } from 'react';
import {
  createBrowserRouter,
  createRoutesFromElements,
  Navigate,
  Route,
  RouterProvider,
} from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Auth Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import VerifyEmail from './pages/auth/VerifyEmail';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';

// Public Pages
import Home from './pages/public/Home';
import Technology from './pages/public/Technology';
import Pricing from './pages/public/Pricing';

// Studio Pages
import Studio from './pages/studio/Studio';
import QuickSetup from './pages/studio/QuickSetup';

// User Pages
import Wardrobe from './pages/user/Wardrobe';
import Billing from './pages/user/Billing';
import ProfileDashboard from './pages/user/ProfileDashboard';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';

// Layouts & Global Components
import AppLayout from './components/layout/AppLayout';
import PublicLayout from './components/layout/PublicLayout';
import { createLogger } from './lib/logger';
import { useAuthStore } from './store/authStore';

const logger = createLogger('VFR.Web.App');

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
    logger.warn('Blocked navigation to admin route for non-admin user.', {
      route: '/admin',
      role,
    });
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

const router = createBrowserRouter(
  createRoutesFromElements(
    <>
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
    </>,
  ),
);

export default function App() {
  return (
    <>
      <Toaster 
        position="bottom-right" 
        toastOptions={{ 
          className: 'dark:bg-gray-800 dark:text-white glass-card', 
          duration: 3000 
        }} 
      />
      <RouterProvider router={router} />
    </>
  );
}
