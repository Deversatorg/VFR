import type { ReactNode } from 'react';
import MarketingNavbar from './MarketingNavbar';
import Footer from './Footer';

interface PublicLayoutProps {
    children: ReactNode;
}

export default function PublicLayout({ children }: PublicLayoutProps) {
    // We don't render Footer on the exact root '/' if it conflicts with the 3D full screen, 
    // but the Home page was modified to scroll down, so we do want the Footer now.

    return (
        <div className="relative min-h-screen bg-[#050505] text-white font-sans overflow-x-hidden flex flex-col">
            <MarketingNavbar />

            <main className="flex-1 w-full relative z-10">
                {children}
            </main>

            <Footer />
        </div>
    );
}
