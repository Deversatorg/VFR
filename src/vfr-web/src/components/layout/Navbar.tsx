import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Ruler, Activity, Camera, Settings, LogOut } from 'lucide-react';

export default function Navbar() {
    const { isAuthenticated, logout } = useAuthStore();
    const location = useLocation();

    // Do not show the main navbar on the login/register/setup pages to keep them focused
    if (!isAuthenticated || location.pathname === '/setup') {
        return (
            <nav className="absolute top-0 left-0 w-full z-50 px-6 py-6 flex justify-between items-center pointer-events-none">
                <div className="flex items-center gap-2 pointer-events-auto cursor-pointer" onClick={() => window.location.href = '/'}>
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 flex items-center justify-center shadow-inner">
                        <Ruler className="w-4 h-4 text-primary" />
                    </div>
                    <span className="text-white font-bold tracking-tight">Deversator<span className="text-primary">.VFR</span></span>
                </div>
                {!isAuthenticated && location.pathname !== '/login' && (
                    <Link to="/login" className="pointer-events-auto px-5 py-2 rounded-full border border-white/10 bg-white/5 hover:bg-white/10 text-white text-sm font-medium transition-all backdrop-blur-md">
                        Sign In
                    </Link>
                )}
            </nav>
        );
    }

    return (
        <nav className="fixed top-0 left-0 w-full z-50 px-6 py-4 flex justify-between items-center backdrop-blur-xl bg-[#0a0a0a]/70 border-b border-white/[0.04] shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
            <Link to="/" className="flex items-center gap-3 group">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 flex items-center justify-center shadow-inner group-hover:border-primary/50 transition-colors">
                    <Ruler className="w-5 h-5 text-primary group-hover:scale-110 transition-transform duration-300" />
                </div>
                <span className="text-white font-bold tracking-tight text-lg">Deversator<span className="text-primary">.VFR</span></span>
            </Link>

            <div className="hidden md:flex items-center gap-1 p-1.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
                <Link to="/studio" className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${location.pathname === '/studio' ? 'bg-white/10 text-white shadow-inner' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
                    <Camera className="w-4 h-4" />
                    Studio
                </Link>
                <Link to="/metrics" className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${location.pathname === '/metrics' ? 'bg-white/10 text-white shadow-inner' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
                    <Activity className="w-4 h-4" />
                    Metrics
                </Link>
            </div>

            <div className="flex items-center gap-3">
                <Link to="/settings" className="w-10 h-10 flex items-center justify-center rounded-xl bg-[#111111] border border-white/[0.06] text-gray-400 hover:text-white hover:border-primary/30 transition-all">
                    <Settings className="w-4 h-4" />
                </Link>
                <button
                    onClick={() => logout()}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 hover:text-red-300 transition-all text-sm font-medium"
                >
                    <LogOut className="w-4 h-4" />
                    <span className="hidden sm:inline">Sign Out</span>
                </button>
            </div>
        </nav>
    );
}
