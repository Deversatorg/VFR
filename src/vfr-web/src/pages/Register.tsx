import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authClient } from '../api/apiClients';
import { Fingerprint, MonitorSmartphone, KeySquare } from 'lucide-react';

export default function Register() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
    const [success, setSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setFieldErrors({});

        if (password !== confirmPassword) {
            setFieldErrors({ confirmpassword: ["Passwords do not match."] });
            return;
        }

        setIsLoading(true);
        try {
            await authClient.post('/api/v1/users', { email, password, confirmPassword });
            setSuccess(true);
            setTimeout(() => navigate('/login'), 2500);
        } catch (err: any) {
            if (err.response?.data?.errors) {
                setFieldErrors(err.response.data.errors);
            }
            setError(err.response?.data?.detail || err.response?.data?.title || 'Registration failed. Please check your credentials.');
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
                <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-emerald-800/10 rounded-full blur-[120px] -translate-x-1/3 translate-y-1/3 pointer-events-none" />

                <div className="relative z-10 max-w-2xl px-8">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-md shadow-[0_0_15px_rgba(255,255,255,0.05)]">
                        <KeySquare className="w-4 h-4 text-emerald-400" />
                        <span className="text-[11px] font-semibold tracking-widest text-[#a1a1aa] uppercase">Secure Global Access</span>
                    </div>

                    <h1 className="text-6xl xl:text-7xl font-bold tracking-tight mb-8 leading-[1.15]">
                        <span className="text-white">Join the digital</span>
                        <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-primary">Revolution.</span>
                    </h1>

                    <p className="text-xl text-gray-400 leading-relaxed font-light max-w-lg">
                        Create an account to digitize your physical form. We use advanced neural rendering for millimetre-accurate virtual try-ons.
                    </p>

                    <div className="mt-16 flex gap-4">
                        <div className="w-12 h-1 bg-white/20 rounded-full overflow-hidden">
                            <div className="w-2/3 h-full bg-emerald-500 rounded-full"></div>
                        </div>
                        <div className="w-12 h-1 bg-white/10 rounded-full"></div>
                        <div className="w-12 h-1 bg-white/10 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Right Register Section */}
            <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 relative z-10">
                {/* Mobile Decorative Orb */}
                <div className="absolute top-0 left-1/2 w-full h-[50vh] bg-emerald-500/20 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 lg:hidden pointer-events-none" />

                <div className="w-full max-w-[420px] backdrop-blur-3xl bg-[#0a0a0a]/80 p-10 sm:p-12 rounded-[2.5rem] border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
                    <div className="mb-10 text-center">
                        <div className="w-16 h-16 bg-gradient-to-b from-gray-800 to-gray-900 border border-white/10 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-inner relative overflow-hidden group">
                            <div className="absolute inset-0 bg-emerald-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <Fingerprint className="w-7 h-7 text-white relative z-10" strokeWidth={1.5} />
                        </div>
                        <h2 className="text-[28px] font-semibold text-white tracking-tight mb-2">Create Account</h2>
                        <p className="text-[#a1a1aa] text-sm">Secure biometric initialization</p>
                    </div>

                    {error && (
                        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0 mt-1.5 box-shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                            <p className="leading-relaxed">{error}</p>
                        </div>
                    )}

                    {success && (
                        <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0 mt-1.5 box-shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                            <p className="leading-relaxed">Registration successful! Redirecting to login...</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-1.5">
                            <label className={`text-[12px] font-medium uppercase tracking-widest ml-1 ${fieldErrors.email ? 'text-red-400' : 'text-gray-400'}`}>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => { setEmail(e.target.value); if (fieldErrors.email) setFieldErrors(prev => ({ ...prev, email: [] })); }}
                                required
                                placeholder="name@example.com"
                                className={`w-full px-5 py-4 bg-[#111111] border ${fieldErrors.email && fieldErrors.email.length > 0 ? 'border-red-500/50 focus:ring-red-500 focus:border-red-500' : 'border-white/[0.06] focus:ring-emerald-500 focus:border-emerald-500'} rounded-2xl text-white placeholder-gray-600 focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner`}
                            />
                            {fieldErrors.email && fieldErrors.email.length > 0 && (
                                <p className="text-red-400 text-[11px] ml-2 mt-1 font-medium">{fieldErrors.email[0]}</p>
                            )}
                        </div>

                        <div className="space-y-1.5">
                            <label className={`text-[12px] font-medium uppercase tracking-widest ml-1 ${fieldErrors.password ? 'text-red-400' : 'text-gray-400'}`}>Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={e => { setPassword(e.target.value); if (fieldErrors.password) setFieldErrors(prev => ({ ...prev, password: [] })); }}
                                required
                                placeholder="••••••••"
                                className={`w-full px-5 py-4 bg-[#111111] border ${fieldErrors.password && fieldErrors.password.length > 0 ? 'border-red-500/50 focus:ring-red-500 focus:border-red-500' : 'border-white/[0.06] focus:ring-emerald-500 focus:border-emerald-500'} rounded-2xl text-white placeholder-gray-600 focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner`}
                            />
                            {fieldErrors.password && fieldErrors.password.length > 0 && (
                                <p className="text-red-400 text-[11px] ml-2 mt-1 font-medium">{fieldErrors.password[0]}</p>
                            )}
                        </div>

                        <div className="space-y-1.5 mb-2">
                            <label className={`text-[12px] font-medium uppercase tracking-widest ml-1 ${fieldErrors.confirmpassword ? 'text-red-400' : 'text-gray-400'}`}>Confirm Password</label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={e => { setConfirmPassword(e.target.value); if (fieldErrors.confirmpassword) setFieldErrors(prev => ({ ...prev, confirmpassword: [] })); }}
                                required
                                placeholder="••••••••"
                                className={`w-full px-5 py-4 bg-[#111111] border ${fieldErrors.confirmpassword && fieldErrors.confirmpassword.length > 0 ? 'border-red-500/50 focus:ring-red-500 focus:border-red-500' : 'border-white/[0.06] focus:ring-emerald-500 focus:border-emerald-500'} rounded-2xl text-white placeholder-gray-600 focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner`}
                            />
                            {fieldErrors.confirmpassword && fieldErrors.confirmpassword.length > 0 && (
                                <p className="text-red-400 text-[11px] ml-2 mt-1 font-medium">{fieldErrors.confirmpassword[0]}</p>
                            )}
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading || success}
                            className="w-full py-4 px-4 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white font-medium rounded-2xl transition-all duration-300 shadow-[0_0_30px_rgba(16,185,129,0.25)] disabled:opacity-70 disabled:active:scale-100 flex justify-center items-center mt-8 relative overflow-hidden group"
                        >
                            <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-[150%] group-hover:translate-x-[150%] transition-transform duration-1000 ease-in-out" />
                            {isLoading ? (
                                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                            ) : success ? 'Vault Generated' : 'Initialize Account'}
                        </button>
                    </form>

                    <div className="mt-8 flex items-center justify-between gap-4">
                        <div className="h-[1px] bg-white/[0.06] flex-1" />
                        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-widest">Connect with</span>
                        <div className="h-[1px] bg-white/[0.06] flex-1" />
                    </div>

                    <div className="mt-6">
                        <button type="button" onClick={() => navigate('/login')} className="w-full flex items-center justify-center gap-3 py-3.5 px-4 bg-[#111111] hover:bg-[#1a1a1a] border border-white/[0.06] rounded-2xl transition-all duration-200 text-sm font-medium text-gray-300 hover:text-white">
                            <MonitorSmartphone className="w-4 h-4 text-emerald-400" />
                            Already have an account? Sign In
                        </button>
                    </div>

                    <p className="mt-8 text-center text-[11px] text-gray-500 font-medium leading-relaxed">
                        By proceeding, you agree to the <br />
                        <a href="#" className="text-gray-400 hover:text-white transition-colors underline decoration-white/20 underline-offset-2">Biometric Data Policy</a> and{' '}
                        <a href="#" className="text-gray-400 hover:text-white transition-colors underline decoration-white/20 underline-offset-2">Terms of Service</a>.
                    </p>
                </div>
            </div>
        </div>
    );
}
