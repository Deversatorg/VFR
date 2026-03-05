import type { ReactNode } from 'react';
import Navbar from './Navbar';
import { useLocation } from 'react-router-dom';

interface AppLayoutProps {
    children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
    const location = useLocation();
    const isStudio = location.pathname === '/studio' || location.pathname === '/avatar';

    return (
        <div className="min-h-screen bg-[#050505] text-white font-sans flex flex-col pt-20">
            <Navbar />

            {/* If we are in the 3D Studio, we want a full screen workspace without scroll. Otherwise normal flow */}
            <main className={`flex-1 relative ${isStudio ? 'overflow-hidden flex bg-black' : 'max-w-7xl mx-auto w-full p-6 sm:p-8'}`}>
                {children}
            </main>

            {/* Ambient Background Glows restricted to non-studio pages to save GPU for 3D */}
            {!isStudio && (
                <>
                    <div className="fixed top-0 left-0 w-full h-[500px] bg-primary/5 rounded-full blur-[150px] -translate-y-1/2 pointer-events-none z-[-1]" />
                    <div className="fixed bottom-0 right-0 w-[600px] h-[600px] bg-blue-900/10 rounded-full blur-[150px] translate-x-1/3 translate-y-1/3 pointer-events-none z-[-1]" />
                </>
            )}
        </div>
    );
}
