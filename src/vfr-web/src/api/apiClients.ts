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
