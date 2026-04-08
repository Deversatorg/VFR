import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';
import { createLogger, createRequestId, getClientSessionId } from '../lib/logger';

// Vite exposes environment variables via import.meta.env (prefixed with VITE_)
// When running under Aspire, these are injected at build/dev time via vite.config.ts define block.
const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:1310';
const PROFILE_API_URL = import.meta.env.VITE_PROFILE_API_URL || 'https://localhost:7107';
const AVATAR_API_URL = import.meta.env.VITE_AI_ENGINE_API_URL || 'http://localhost:8000';
const apiLogger = createLogger('VFR.Web.Api');

type RequestMetadata = {
    requestId: string;
    startedAt: number;
};

type RequestConfigWithMetadata = InternalAxiosRequestConfig & {
    metadata?: RequestMetadata;
};

function setHeader(config: InternalAxiosRequestConfig, name: string, value: string) {
    config.headers.set(name, value);
}

function attachObservabilityHeaders(config: RequestConfigWithMetadata) {
    const requestId = createRequestId();

    setHeader(config, 'X-Request-ID', requestId);
    setHeader(config, 'X-Client-Session-ID', getClientSessionId());
    config.metadata = {
        requestId,
        startedAt: Date.now(),
    };

    return config;
}

function attachFailureLogging(clientName: string, client: AxiosInstance) {
    client.interceptors.response.use(
        response => response,
        (error: AxiosError) => {
            const config = error.config as RequestConfigWithMetadata | undefined;
            const elapsedMs = config?.metadata
                ? Date.now() - config.metadata.startedAt
                : undefined;

            apiLogger.error(
                'HTTP request failed',
                {
                    client: clientName,
                    method: config?.method?.toUpperCase(),
                    url: config?.url,
                    status_code: error.response?.status,
                    request_id: config?.metadata?.requestId,
                    server_request_id: error.response?.headers?.['x-request-id'],
                    elapsed_ms: elapsedMs,
                },
                error);

            return Promise.reject(error);
        });
}

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

profileClient.interceptors.request.use((config) => {
    const nextConfig = attachObservabilityHeaders(config as RequestConfigWithMetadata);
    const token = useAuthStore.getState().token;
    if (token) {
        setHeader(nextConfig, 'Authorization', `Bearer ${token}`);
    }
    return nextConfig;
});

authClient.interceptors.request.use((config) => {
    const nextConfig = attachObservabilityHeaders(config as RequestConfigWithMetadata);
    const token = useAuthStore.getState().token;
    if (token && !config.url?.includes('/account/login') && !config.url?.includes('/users')) {
        setHeader(nextConfig, 'Authorization', `Bearer ${token}`);
    }
    return nextConfig;
});

avatarClient.interceptors.request.use((config) =>
    attachObservabilityHeaders(config as RequestConfigWithMetadata));

attachFailureLogging('auth', authClient);
attachFailureLogging('profile', profileClient);
attachFailureLogging('avatar', avatarClient);

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
