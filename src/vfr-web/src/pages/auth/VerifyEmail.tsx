import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { SessionApi, getApiErrorMessage } from '../../api/apiClients';
import { MailCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'react-hot-toast';

export default function VerifyEmail() {
    const location = useLocation();
    const [email, setEmail] = useState(location.state?.email || '');
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');
        setSuccess('');
        try {
            await SessionApi.verifyEmail({ email, code });
            const msg = 'Email successfully verified! You can now log in.';
            setSuccess(msg);
            toast.success(msg);
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            const errMsg = getApiErrorMessage(err, 'Verification failed. Invalid code.');
            setError(errMsg);
            toast.error(errMsg);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full bg-[#050505] font-sans text-white flex justify-center items-center p-6 relative overflow-hidden">
            {/* Dark abstract bg layer */}
            <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/20 rounded-full blur-[150px] translate-x-1/2 -translate-y-1/2 pointer-events-none" />
            
            <motion.div 
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="w-full max-w-[420px] backdrop-blur-3xl bg-[#0a0a0a]/80 p-10 sm:p-12 rounded-[2.5rem] border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-10"
            >
                <div className="mb-10 text-center">
                    <div className="w-16 h-16 bg-gradient-to-b from-gray-800 to-gray-900 border border-white/10 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-inner relative overflow-hidden group">
                        <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        <MailCheck className="w-7 h-7 text-white relative z-10" />
                    </div>
                    <h2 className="text-[28px] font-semibold text-white tracking-tight mb-2">Verify Email</h2>
                    <p className="text-[#a1a1aa] text-sm">Enter the code sent to your inbox</p>
                </div>

                {error && (
                    <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm animate-in fade-in slide-in-from-top-2">
                        <p>{error}</p>
                    </div>
                )}
                {success && (
                    <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm animate-in fade-in slide-in-from-top-2">
                        <p>{success}</p>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="space-y-1.5">
                        <label className="text-[12px] font-medium uppercase tracking-widest text-gray-400 ml-1">Email Address</label>
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            placeholder="name@example.com"
                            className="w-full px-5 py-4 bg-[#111111] border border-white/[0.06] focus:ring-primary focus:border-primary rounded-2xl text-white placeholder-gray-600 focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[12px] font-medium uppercase tracking-widest text-gray-400 ml-1">Verification Code</label>
                        <input
                            type="text"
                            value={code}
                            onChange={e => setCode(e.target.value)}
                            required
                            placeholder="123456"
                            className="w-full px-5 py-4 bg-[#111111] border border-white/[0.06] focus:ring-primary focus:border-primary rounded-2xl text-white placeholder-gray-600 tracking-[0.5em] text-center font-mono focus:ring-1 focus:outline-none transition-all duration-300 shadow-inner"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full py-4 px-4 bg-primary hover:bg-primary-dark active:scale-[0.98] text-white font-medium rounded-2xl transition-all duration-300 shadow-[0_0_30px_rgba(19,91,236,0.25)] disabled:opacity-70 flex justify-center mt-6"
                    >
                        {isLoading ? 'Verifying...' : 'Verify Email'}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <button onClick={() => navigate('/login')} className="text-sm font-medium text-gray-400 hover:text-white transition-colors underline decoration-white/20 underline-offset-2">
                        Back to Login
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
