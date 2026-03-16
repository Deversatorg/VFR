import axios from 'axios';
import { useAuthStore } from '../store/authStore';

// Vite exposes environment variables via import.meta.env (prefixed with VITE_)
// When running under Aspire, these are injected at build/dev time via vite.config.ts define block.
const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:1310';
const PROFILE_API_URL = import.meta.env.VITE_PROFILE_API_URL || 'https://localhost:7107';
const AVATAR_API_URL = import.meta.env.VITE_AI_ENGINE_API_URL || 'http://localhost:8000';

export const authClient = axios.create({
    baseURL: AUTH_API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

export const profileClient = axios.create({
    baseURL: PROFILE_API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

export const avatarClient = axios.create({
    baseURL: AVATAR_API_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Interceptor to inject JWT into Profile API requests
profileClient.interceptors.request.use((config) => {
    const token = useAuthStore.getState().token;
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Admin Interceptor (Assume Admin uses the same token, but we could separate if needed)
authClient.interceptors.request.use((config) => {
    const token = useAuthStore.getState().token;
    if (token && !config.url?.includes('/account/login') && !config.url?.includes('/users')) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// === AUTH & SESSIONS ===
export const SessionApi = {
    // Current Login
    login: (data: any) => authClient.post('/api/v1/sessions', data),
    
    // SSO
    loginGoogle: (data: { idToken: string }) => authClient.post('/api/v1/sessions/google', data),
    loginApple: (data: { identityToken: string, givenName?: string, familyName?: string }) => authClient.post('/api/v1/sessions/apple', data),
    
    // Admin login
    adminLogin: (data: any) => authClient.post('/api/v1/admin-sessions', data),
    
    // Management
    verifyEmail: (data: { email: string; code: string }) => authClient.post('/api/v1/sessions/verify-email', data),
    forgotPassword: (data: { email: string }) => authClient.post('/api/v1/sessions/forgot-password', data),
    resetPassword: (data: { email: string; code: string; newPassword: string }) => authClient.post('/api/v1/sessions/reset-password', data),
};

export const UserApi = {
    register: (data: any) => authClient.post('/api/v1/users', data),
};

// === BILLING ===
export const BillingApi = {
    getSubscription: () => authClient.get('/api/v1/payments/subscription'),
    cancelSubscription: () => authClient.post('/api/v1/payments/subscription/cancel'),
    getPlans: () => authClient.get('/api/v1/plans'),
    checkout: (data: { planId: number }) => authClient.post('/api/v1/payments/checkout', data),
};

// === ADMIN ===
export const AdminApi = {
    getUsers: (params?: any) => authClient.get('/api/v1/admin-users', { params }),
    deleteUser: (id: number) => authClient.delete(`/api/v1/admin-users/${id}`),
    getAdmins: (params?: any) => authClient.get('/api/v1/superadmin/admins', { params }),
};
