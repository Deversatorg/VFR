import { Network, Cpu, Database, Zap, Layers, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Technology() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-[#050505] text-white pt-24 pb-16 px-6 font-sans overflow-hidden">
            {/* Background elements */}
            <div className="fixed top-0 left-1/2 w-full max-w-7xl h-full -translate-x-1/2 pointer-events-none z-0">
                <div className="absolute top-[20%] right-[10%] w-[600px] h-[600px] bg-primary/10 rounded-full blur-[120px] mix-blend-screen" />
                <div className="absolute bottom-[20%] left-[10%] w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[120px] mix-blend-screen" />
                <div className="absolute inset-0 opacity-[0.02]" style={{
                    backgroundImage: 'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)',
                    backgroundSize: '50px 50px'
                }} />
            </div>

            <main className="max-w-7xl mx-auto relative z-10">

                {/* Hero Section */}
                <section className="text-center max-w-3xl mx-auto mb-32 animate-[fadeUp_1s_ease-out]">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-md">
                        <Cpu className="w-4 h-4 text-primary" />
                        <span className="text-[11px] font-semibold tracking-widest text-[#a1a1aa] uppercase">VFR Compute Cluster</span>
                    </div>

                    <h1 className="text-5xl sm:text-7xl font-bold tracking-tight mb-8 leading-[1.1]">
                        The <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-emerald-400">Neural Engine</span>
                    </h1>

                    <p className="text-xl text-gray-400 leading-relaxed font-light">
                        We don't just dress 3D models. We compile hyper-realistic physical volumes in real-time using proprietary transformer architectures.
                    </p>
                </section>

                {/* Architecture Pipeline */}
                <section className="mb-32">
                    <div className="grid md:grid-cols-3 gap-8">
                        {/* Step 1 */}
                        <div className="glass-card p-10 rounded-3xl relative overflow-hidden group hover:border-primary/30 transition-all duration-500">
                            <div className="absolute top-0 right-0 p-6 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 group-hover:opacity-20 transition-all duration-700">
                                <ScanLine className="w-48 h-48 text-primary" />
                            </div>
                            <div className="w-14 h-14 bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 rounded-2xl flex items-center justify-center mb-8 shadow-inner">
                                <Database className="w-6 h-6 text-gray-300" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3">1. Biometric Ingestion</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                Client metrics are securely ingested and normalized. Our .NET 8 Aspire layer ensures isolated micro-tenant environments for absolute data privacy and SOC2 compliance.
                            </p>
                        </div>

                        {/* Step 2 */}
                        <div className="glass-card p-10 rounded-3xl relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-500 md:translate-y-8">
                            <div className="absolute top-0 right-0 p-6 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 group-hover:opacity-20 transition-all duration-700">
                                <Layers className="w-48 h-48 text-emerald-500" />
                            </div>
                            <div className="w-14 h-14 bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 rounded-2xl flex items-center justify-center mb-8 shadow-inner">
                                <Network className="w-6 h-6 text-emerald-400" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3">2. Volumetric Compilation</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                The Python Celery workers map 2D data to a 3D topology. SMPL-X models are dynamically generated via GPU-accelerated PyTorch workers.
                            </p>
                        </div>

                        {/* Step 3 */}
                        <div className="glass-card p-10 rounded-3xl relative overflow-hidden group hover:border-blue-500/30 transition-all duration-500 md:translate-y-16">
                            <div className="absolute top-0 right-0 p-6 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 group-hover:opacity-20 transition-all duration-700">
                                <Zap className="w-48 h-48 text-blue-500" />
                            </div>
                            <div className="w-14 h-14 bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 rounded-2xl flex items-center justify-center mb-8 shadow-inner">
                                <Zap className="w-6 h-6 text-blue-400" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3">3. Neural Rendering</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                Assets are streamed via gRPC directly to the React Three Fiber viewport. Cloth physics are simulated locally using WebAssembly, ensuring sub-50ms latency.
                            </p>
                        </div>
                    </div>
                </section>

                {/* Tech Stack Banner */}
                <section className="glass-card rounded-[3rem] p-12 sm:p-20 relative overflow-hidden text-center">
                    <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />

                    <h2 className="text-3xl font-semibold mb-12">Built on Industry Standards</h2>

                    <div className="flex flex-wrap justify-center items-center gap-12 sm:gap-24 opacity-60">
                        {/* Placeholder tech logos text */}
                        <span className="text-2xl font-black tracking-tighter">.NET 8</span>
                        <span className="text-2xl font-bold font-mono">PyTorch</span>
                        <span className="text-2xl font-bold font-sans">React<span className="text-primary tracking-widest text-lg font-normal"> / THREE</span></span>
                        <span className="text-2xl font-semibold tracking-wide">PostgreSQL</span>
                    </div>

                    <button
                        onClick={() => navigate('/register')}
                        className="mt-16 px-8 py-4 bg-white text-black hover:bg-gray-100 rounded-full font-medium transition-all group inline-flex items-center gap-3"
                    >
                        Initialize Your Node
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </button>
                </section>

            </main>
        </div>
    );
}
// Adding ScanLine directly here since it's used in the logic
function ScanLine(props: any) {
    return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" /><path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" /><path d="M7 12h10" /></svg>;
}
