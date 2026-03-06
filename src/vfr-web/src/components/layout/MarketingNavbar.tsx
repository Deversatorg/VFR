import { Link } from 'react-router-dom';
import { Box } from 'lucide-react';

export default function MarketingNavbar() {
    return (
        <nav className="absolute top-0 w-full z-50 px-6 py-8 sm:px-12 flex justify-between items-center pointer-events-auto">
            <Link to="/" className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 flex items-center justify-center shadow-inner relative overflow-hidden group">
                    <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <Box className="w-5 h-5 text-primary relative z-10" />
                </div>
                <span className="text-white font-bold tracking-tight text-xl hidden sm:inline-block">Deversator<span className="text-primary">.VFR</span></span>
            </Link>

            <div className="hidden md:flex items-center gap-8 text-sm font-medium">
                <Link to="/technology" className="text-gray-300 hover:text-white hover:text-shadow-[0_0_10px_rgba(255,255,255,0.5)] transition-all">Technology</Link>
                <Link to="/pricing" className="text-gray-300 hover:text-white hover:text-shadow-[0_0_10px_rgba(255,255,255,0.5)] transition-all">Pricing</Link>
            </div>

            <div className="flex items-center gap-4 sm:gap-6">
                <Link to="/login" className="text-sm font-medium text-gray-400 hover:text-white transition-colors">Sign In</Link>
                <Link to="/register" className="px-5 py-2.5 sm:px-6 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white text-sm font-medium transition-all backdrop-blur-md hover:scale-105 active:scale-95">
                    Get Started
                </Link>
            </div>
        </nav>
    );
}
