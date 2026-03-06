import { Link } from 'react-router-dom';
import { Box } from 'lucide-react';

export default function Footer() {
    return (
        <footer className="relative z-20 border-t border-white/[0.03] bg-[#050505] py-16 px-6">
            <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start gap-12">
                <div className="max-w-sm">
                    <div className="flex items-center gap-2 mb-6">
                        <Box className="w-5 h-5 text-gray-500" />
                        <span className="font-bold tracking-tight text-xl text-white">Deversator<span className="text-primary">.VFR</span></span>
                    </div>
                    <p className="text-sm text-gray-500 leading-relaxed">
                        Pioneering the next intersection of deep learning and retail. Sub-millimeter neural rendering for global commerce.
                    </p>
                </div>

                <div className="flex gap-16">
                    <div>
                        <h4 className="text-white font-semibold mb-4 text-sm">Product</h4>
                        <ul className="space-y-3 text-sm text-gray-400">
                            <li><Link to="/technology" className="hover:text-primary transition-colors">Neural Engine</Link></li>
                            <li><Link to="/pricing" className="hover:text-primary transition-colors">Pricing</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="text-white font-semibold mb-4 text-sm">Legal</h4>
                        <ul className="space-y-3 text-sm text-gray-400">
                            <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">SOC2 Compliance</a></li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto mt-16 pt-8 border-t border-white/[0.03] flex justify-between items-center text-xs text-gray-600 font-medium">
                <p>© 2026 Deversator Neural Networks. All rights reserved.</p>
                <div className="flex gap-4">
                    <span className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        Systems Operational
                    </span>
                </div>
            </div>
        </footer>
    );
}
