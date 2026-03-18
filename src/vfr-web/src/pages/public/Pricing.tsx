import { CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Pricing() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-[#050505] text-white pt-24 pb-20 px-6 font-sans">
            <div className="max-w-7xl mx-auto">
                <div className="text-center max-w-3xl mx-auto mb-20 animate-[fadeUp_1s_ease-out]">
                    <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
                        Scale your <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-emerald-400">Digital Try-On</span>
                    </h1>
                    <p className="text-xl text-gray-400 font-light">
                        Enterprise-grade infrastructure. Transparent pricing.
                    </p>
                </div>

                <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                    {/* Developer Tier */}
                    <div className="glass-card p-10 rounded-[2.5rem] border border-white/[0.05] flex flex-col hover:-translate-y-2 transition-transform duration-300">
                        <div className="mb-8">
                            <h3 className="text-xl font-medium text-gray-300 mb-2">Developer</h3>
                            <div className="flex items-baseline gap-2">
                                <span className="text-4xl font-semibold">$0</span>
                                <span className="text-sm text-gray-500">/mo</span>
                            </div>
                            <p className="text-sm text-gray-400 mt-4 leading-relaxed">Perfect for integrating the SDK into sandbox environments.</p>
                        </div>

                        <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent mb-8" />

                        <ul className="space-y-4 mb-10 flex-1">
                            {['Up to 500 Avatar Generations', 'Standard Mesh Output (1M Poly)', 'Community Support', 'Watermarked 3D Viewer'].map((feature, i) => (
                                <li key={i} className="flex items-start gap-3">
                                    <CheckCircle2 className="w-5 h-5 text-gray-500 shrink-0" />
                                    <span className="text-sm text-gray-300 leading-tight">{feature}</span>
                                </li>
                            ))}
                        </ul>

                        <button onClick={() => navigate('/register')} className="w-full py-4 rounded-xl bg-white/5 hover:bg-white/10 text-white text-sm font-medium transition-colors">
                            Start Building
                        </button>
                    </div>

                    {/* Pro Tier */}
                    <div className="glass-card p-10 rounded-[2.5rem] border border-primary/50 bg-[#0a0a0a] flex flex-col relative transform md:-translate-y-4 shadow-[0_0_50px_rgba(19,91,236,0.15)]">
                        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-primary to-transparent" />
                        <div className="absolute top-4 right-6">
                            <span className="px-3 py-1 bg-primary/20 text-primary text-[10px] font-bold uppercase tracking-widest rounded-full">Most Popular</span>
                        </div>

                        <div className="mb-8">
                            <h3 className="text-xl font-medium text-primary mb-2">Commerce Pro</h3>
                            <div className="flex items-baseline gap-2">
                                <span className="text-4xl font-semibold">$499</span>
                                <span className="text-sm text-gray-500">/mo</span>
                            </div>
                            <p className="text-sm text-gray-400 mt-4 leading-relaxed">For growing D2C brands heavily leveraging virtual fittings.</p>
                        </div>

                        <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent mb-8" />

                        <ul className="space-y-4 mb-10 flex-1">
                            {['Up to 10,000 Generations', 'High Fidelity Output (4M Poly)', 'Garment Physics Engine', 'Unbranded Viewer SDK', 'Priority Email Support'].map((feature, i) => (
                                <li key={i} className="flex items-start gap-3">
                                    <CheckCircle2 className="w-5 h-5 text-primary shrink-0" />
                                    <span className="text-sm text-white leading-tight">{feature}</span>
                                </li>
                            ))}
                        </ul>

                        <button onClick={() => navigate('/register')} className="w-full py-4 rounded-xl bg-primary hover:bg-primary-dark text-white text-sm font-medium transition-colors shadow-[0_0_20px_rgba(19,91,236,0.2)]">
                            Upgrade to Pro
                        </button>
                    </div>

                    {/* Enterprise Tier */}
                    <div className="glass-card p-10 rounded-[2.5rem] border border-white/[0.05] flex flex-col hover:-translate-y-2 transition-transform duration-300">
                        <div className="mb-8">
                            <h3 className="text-xl font-medium text-gray-300 mb-2">Enterprise</h3>
                            <div className="flex items-baseline gap-2">
                                <span className="text-4xl font-semibold">Custom</span>
                            </div>
                            <p className="text-sm text-gray-400 mt-4 leading-relaxed">Dedicated infrastructure for immense scale.</p>
                        </div>

                        <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent mb-8" />

                        <ul className="space-y-4 mb-10 flex-1">
                            {['Unlimited Generations', 'On-Premise or Dedicated VPC', 'Custom Model Weights', '24/7 SLA Support', 'Dedicated Success Architect'].map((feature, i) => (
                                <li key={i} className="flex items-start gap-3">
                                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                                    <span className="text-sm text-gray-300 leading-tight">{feature}</span>
                                </li>
                            ))}
                        </ul>

                        <button className="w-full py-4 rounded-xl bg-white text-black hover:bg-gray-100 text-sm font-medium transition-colors">
                            Contact Sales
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
