import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authClient } from '../api/apiClients';
import { Fingerprint, MonitorSmartphone } from 'lucide-react';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
    const [isLoading, setIsLoading] = useState(false);

    const login = useAuthStore(state => state.login);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');
        setFieldErrors({});
        try {
            const response = await authClient.post('/api/v1/sessions', { email, password });
            // Backend returns: { data: { user: {...}, token: { accessToken: "...", refreshToken: "..." } } }
            const token = response.data?.data?.token?.accessToken;
            if (token) {
                login(token);
                navigate('/setup');
            }
        } catch (err: any) {
            if (err.response?.data?.errors) {
                setFieldErrors(err.response.data.errors);
            }
            setError(err.response?.data?.detail || err.response?.data?.title || 'Login failed. Please check your credentials.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full bg-[#050505] font-sans text-white flex">
            {/* Left Hero Section - Hidden on mobile */}
            <div className="hidden lg:flex flex-col justify-center relative w-[55%] p-16 overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-gray-900 via-[#050505] to-[#050505] border-r border-white/5">
                {/* Decorative Background Elements */}
                <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-primary/20 rounded-full blur-[150px] translate-x-1/2 -translate-y-1/2 pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-800/10 rounded-full blur-[120px] -translate-x-1/3 translate-y-1/3 pointer-events-none" />

                <div className="relative z-10 max-w-2xl px-8">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-md shadow-[0_0_15px_rgba(255,255,255,0.05)]">
                        <Fingerprint className="w-4 h-4 text-primary" />
                        <span className="text-[11px] font-semibold tracking-widest text-[#a1a1aa] uppercase">Secure Biometric Setup Next</span>
                    </div>

                    <h1 className="text-6xl xl:text-7xl font-bold tracking-tight mb-8 leading-[1.15]">
                        <span className="text-white">Your perfect fit.</span>
                        <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-light to-primary">Computed.</span>
                    </h1>

                    <p className="text-xl text-gray-400 leading-relaxed font-light max-w-lg">
                        Experience the next generation of virtual fitting powered by neural rendering. Log in to access your personal fitting room.
                    </p>

                    <div className="mt-16 flex gap-4">
                        <div className="w-12 h-1 bg-white/20 rounded-full overflow-hidden">
                            <div className="w-2/3 h-full bg-primary rounded-full"></div>
                        </div>
                        <div className="w-12 h-1 bg-white/10 rounded-full"></div>
                        <div className="w-12 h-1 bg-white/10 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Right Login Section */}
            <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 relative z-10">
                {/* Mobile Decorative Orb */}
                <div className="absolute top-0 left-1/2 w-full h-[50vh] bg-primary/20 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 lg:hidden pointer-events-none" />

                <div className="w-full max-w-[420px] backdrop-blur-3xl bg-[#0a0a0a]/80 p-10 sm:p-12 rounded-[2.5rem] border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
                    <div className="mb-10 text-center">
                        <div className="w-16 h-16 bg-gradient-to-b from-gray-800 to-gray-900 border border-white/10 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-inner relative overflow-hidden group">
                            <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <MonitorSmartphone className="w-7 h-7 text-white relative z-10" strokeWidth={1.5} />
                        </div>
                        <h2 className="text-[28px] font-semibold text-white tracking-tight mb-2">Welcome back</h2>
                        <p className="text-[#a1a1aa] text-sm">Please enter your credentials to continue</p>
                    </div>

                    {error && (
                        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0 mt-1.5 box-shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                            <p className="leading-relaxed">{error}</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-1.5">
                            <label className={`text-[12px] font-medium uppercase tracking-widest ml-1 ${fieldErrors.email ? 'text-red-400' : 'text-gray-400'}`}>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => { setEmail(e.target.value); if (fieldErrors.email) setFieldErrors(prev => ({ ...prev, email: [] })); }}
                                required
                                placeholder="name@example.com"
                                className={`w-full px-5 py-4 bg-[#111111] border ${fieldErrors.email && fieldErrors.email.length > 0 ? 'border-red-500/50 focus:ring-red-500 focus:border-red-500' : 'border-white/[0.06] focus:ring-primary focus:border-primary'} rounded-2xl text-white placeholder-gray-600 focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner`}
                            />
                            {fieldErrors.email && fieldErrors.email.length > 0 && (
                                <p className="text-red-400 text-[11px] ml-2 mt-1 font-medium">{fieldErrors.email[0]}</p>
                            )}
                        </div>

                        <div className="space-y-1.5">
                            <div className="flex justify-between items-center ml-1">
                                <label className={`text-[12px] font-medium uppercase tracking-widest ${fieldErrors.password ? 'text-red-400' : 'text-gray-400'}`}>Password</label>
                                <a href="#" className="text-[12px] font-medium text-primary hover:text-white transition-colors duration-200">Forgot?</a>
                            </div>
                            <input
                                type="password"
                                value={password}
                                onChange={e => { setPassword(e.target.value); if (fieldErrors.password) setFieldErrors(prev => ({ ...prev, password: [] })); }}
                                required
                                placeholder="••••••••"
                                className={`w-full px-5 py-4 bg-[#111111] border ${fieldErrors.password && fieldErrors.password.length > 0 ? 'border-red-500/50 focus:ring-red-500 focus:border-red-500' : 'border-white/[0.06] focus:ring-primary focus:border-primary'} rounded-2xl text-white placeholder-gray-600 focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner`}
                            />
                            {fieldErrors.password && fieldErrors.password.length > 0 && (
                                <p className="text-red-400 text-[11px] ml-2 mt-1 font-medium">{fieldErrors.password[0]}</p>
                            )}
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-4 px-4 bg-primary hover:bg-primary-dark active:scale-[0.98] text-white font-medium rounded-2xl transition-all duration-300 shadow-[0_0_30px_rgba(19,91,236,0.25)] disabled:opacity-70 disabled:active:scale-100 flex justify-center items-center mt-6 relative overflow-hidden group"
                        >
                            <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-[150%] group-hover:translate-x-[150%] transition-transform duration-1000 ease-in-out" />
                            {isLoading ? (
                                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                            ) : 'Sign In'}
                        </button>
                    </form>

                    <div className="mt-8 flex items-center justify-between gap-4">
                        <div className="h-[1px] bg-white/[0.06] flex-1" />
                        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-widest">Or continue with</span>
                        <div className="h-[1px] bg-white/[0.06] flex-1" />
                    </div>

                    <div className="mt-6 grid grid-cols-2 gap-4">
                        <button type="button" className="flex items-center justify-center gap-3 py-3.5 px-4 bg-[#111111] hover:bg-[#1a1a1a] border border-white/[0.06] rounded-2xl transition-all duration-200 text-sm font-medium text-gray-300 hover:text-white">
                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" /></svg>
                            Google
                        </button>
                        <button type="button" className="flex items-center justify-center gap-3 py-3.5 px-4 bg-[#111111] hover:bg-[#1a1a1a] border border-white/[0.06] rounded-2xl transition-all duration-200 text-sm font-medium text-gray-300 hover:text-white">
                            <svg className="w-[18px] h-[18px] text-white" viewBox="0 0 384 512" fill="currentColor"><path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z" /></svg>
                            Apple
                        </button>
                    </div>

                    <p className="mt-8 text-center text-[11px] text-gray-500 font-medium">
                        Protected by reCAPTCHA and subject to the <br />
                        <a href="#" className="text-gray-400 hover:text-white transition-colors underline decoration-white/20 underline-offset-2">Privacy Policy</a> and{' '}
                        <a href="#" className="text-gray-400 hover:text-white transition-colors underline decoration-white/20 underline-offset-2">Terms of Service</a>.
                    </p>
                </div>
            </div>
        </div>
    );
}
