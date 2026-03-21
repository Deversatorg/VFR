import { create } from 'zustand';

interface AuthState {
    token: string | null;
    isAuthenticated: boolean;
    role: string | null;
    email: string | null;
    login: (token: string) => void;
    logout: () => void;
}

const parseJwtRole = (token: string | null): string | null => {
    if (!token) return null;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload['http://schemas.microsoft.com/ws/2008/06/identity/claims/role'] || payload.role || null;
    } catch {
        return null;
    }
};

const parseJwtEmail = (token: string | null): string | null => {
    if (!token) return null;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'] || payload.email || null;
    } catch {
        return null;
    }
};

export const useAuthStore = create<AuthState>((set) => {
    const initialToken = sessionStorage.getItem('vfr_token');
    return {
        token: initialToken,
        isAuthenticated: !!initialToken,
        role: parseJwtRole(initialToken),
        email: parseJwtEmail(initialToken),
        login: (token: string) => {
            sessionStorage.setItem('vfr_token', token);
            set({ token, isAuthenticated: true, role: parseJwtRole(token), email: parseJwtEmail(token) });
        },
        logout: () => {
            sessionStorage.removeItem('vfr_token');
            set({ token: null, isAuthenticated: false, role: null, email: null });
        }
    };
});
