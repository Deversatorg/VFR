import { Link } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { motion } from 'framer-motion';
import { ArrowRight, Box, Zap, Lock, ScanLine, Activity } from 'lucide-react';
import HeroModel from '../components/3d/HeroModel';

export default function Home() {
    return (
        <div className="relative min-h-screen bg-[#050505] text-white font-sans overflow-x-hidden">
            {/* 3D Canvas Background (Full Screen) */}
            <div className="fixed inset-0 z-0">
                <Canvas
                    camera={{ position: [0, 1.5, 6], fov: 45 }}
                    gl={{ antialias: true, alpha: false }}
                    className="w-full h-full"
                >
                    <color attach="background" args={['#050505']} />
                    <fog attach="fog" args={['#050505', 5, 15]} />
                    <HeroModel />
                </Canvas>
                {/* Global Vignette/Shadow overlay to ensure text readability */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(5,5,5,0.85)_100%)] pointer-events-none" />
                {/* Left side darkening gradient for primary text area */}
                <div className="absolute inset-0 bg-gradient-to-r from-[#050505] via-[#050505]/70 to-transparent pointer-events-none w-[70%]" />
            </div>

            {/* Navbar */}
            <nav className="absolute top-0 w-full z-50 px-6 py-8 sm:px-12 flex justify-between items-center pointer-events-auto">
                <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 flex items-center justify-center shadow-inner relative overflow-hidden group">
                        <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        <Box className="w-5 h-5 text-primary relative z-10" />
                    </div>
                    <span className="text-white font-bold tracking-tight text-xl">Deversator<span className="text-primary">.VFR</span></span>
                </div>
                <div className="flex items-center gap-6">
                    <Link to="/login" className="text-sm font-medium text-gray-400 hover:text-white transition-colors">Sign In</Link>
                    <Link to="/register" className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white text-sm font-medium transition-all backdrop-blur-md">
                        Get Started
                    </Link>
                </div>
            </nav>

            {/* Main Hero Content */}
            <div className="relative z-10 min-h-screen flex items-center px-6 sm:px-12 lg:px-24 pointer-events-none">
                <div className="w-full max-w-2xl mt-20 pointer-events-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 1, ease: "easeOut" }}
                    >
                        {/* Premium Badge */}
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 backdrop-blur-md mb-8 shadow-[0_0_20px_rgba(19,91,236,0.2)]">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                            </span>
                            <span className="text-xs font-semibold tracking-[0.2em] text-primary uppercase">Engine v2.0 Online</span>
                        </div>

                        <h1 className="text-5xl sm:text-7xl lg:text-[5.5rem] font-bold tracking-tight mb-8 leading-[1.05]">
                            <span className="text-white drop-shadow-lg">The future of</span><br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-light via-primary to-blue-600 drop-shadow-[0_0_30px_rgba(19,91,236,0.3)]">virtual fitting.</span>
                        </h1>

                        <p className="text-lg sm:text-xl text-gray-300 max-w-lg mb-12 leading-relaxed font-light drop-shadow-md border-l-2 border-primary/50 pl-6">
                            Generate hyper-realistic, millimetre-accurate neural avatars in seconds. Step into the digital dressing room built for scalable fashion retail.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-5">
                            <Link to="/register" className="inline-flex justify-center items-center gap-3 px-8 py-4.5 bg-primary hover:bg-primary-dark text-white font-medium rounded-2xl transition-all shadow-[0_0_40px_rgba(19,91,236,0.3)] group hover:scale-[1.02] active:scale-[0.98]">
                                <ScanLine className="w-5 h-5 opacity-70" />
                                Initialize Avatar
                                <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
                            </Link>
                            <a href="#metrics" className="inline-flex justify-center items-center gap-3 px-8 py-4.5 bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md text-white font-medium rounded-2xl transition-all hover:border-white/20">
                                <Activity className="w-5 h-5 text-gray-400" />
                                View Metrics
                            </a>
                        </div>
                    </motion.div>
                </div>
            </div>

            {/* Investor Metrics / Features Section */}
            <div id="metrics" className="relative z-20 bg-[#050505] border-t border-white/5 pb-24 pt-32 px-6 sm:px-12 lg:px-24">
                {/* Section header */}
                <div className="max-w-7xl mx-auto mb-20 text-center">
                    <h2 className="text-3xl font-bold mb-4">Enterprise Grade Infrastructure</h2>
                    <p className="text-gray-400 max-w-2xl mx-auto">VFR delivers real-time 3D rendering with scalable cloud architecture designed for seamless high-traffic retail integration.</p>
                </div>

                <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Feature 1 */}
                    <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-100px" }} transition={{ duration: 0.7 }}
                        className="group p-10 rounded-[2.5rem] bg-[#0A0A0A] border border-white/[0.04] hover:border-primary/30 hover:bg-[#0f0f0f] transition-all duration-500 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 group-hover:bg-primary/10 transition-colors duration-500" />
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20 flex items-center justify-center mb-8 shadow-[0_0_15px_rgba(19,91,236,0.1)]">
                            <Zap className="w-6 h-6 text-primary" />
                        </div>
                        <h3 className="text-2xl font-semibold mb-4 text-white">Sub-second Latency</h3>
                        <p className="text-gray-400 text-[15px] leading-relaxed">Our optimized gRPC microservices pipeline calculates millions of biometric parameters to deliver a ready-to-use 3D mesh instantly.</p>
                    </motion.div>

                    {/* Feature 2 */}
                    <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-100px" }} transition={{ duration: 0.7, delay: 0.15 }}
                        className="group p-10 rounded-[2.5rem] bg-[#0A0A0A] border border-white/[0.04] hover:border-blue-500/30 hover:bg-[#0f0f0f] transition-all duration-500 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 group-hover:bg-blue-500/10 transition-colors duration-500" />
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-500/5 border border-blue-500/20 flex items-center justify-center mb-8 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                            <Box className="w-6 h-6 text-blue-400" />
                        </div>
                        <h3 className="text-2xl font-semibold mb-4 text-white">Neural Accuracy</h3>
                        <p className="text-gray-400 text-[15px] leading-relaxed">Unlike basic parametric models, VFR utilizes deep reinforcement learning across thousands of real-world scans for true-to-life topological contours.</p>
                    </motion.div>

                    {/* Feature 3 */}
                    <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-100px" }} transition={{ duration: 0.7, delay: 0.3 }}
                        className="group p-10 rounded-[2.5rem] bg-[#0A0A0A] border border-white/[0.04] hover:border-emerald-500/30 hover:bg-[#0f0f0f] transition-all duration-500 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 group-hover:bg-emerald-500/10 transition-colors duration-500" />
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 border border-emerald-500/20 flex items-center justify-center mb-8 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                            <Lock className="w-6 h-6 text-emerald-400" />
                        </div>
                        <h3 className="text-2xl font-semibold mb-4 text-white">Enterprise Security</h3>
                        <p className="text-gray-400 text-[15px] leading-relaxed">Biometric data is aggressively encrypted at rest. We maintain strict compliance with GDPR, SOC2, and global retail industry privacy standards.</p>
                    </motion.div>
                </div>
            </div>

            {/* Footer */}
            <footer className="relative z-20 border-t border-white/[0.03] bg-[#050505] py-12 px-6">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
                    <div className="flex items-center gap-2 opacity-50">
                        <Box className="w-5 h-5" />
                        <span className="font-bold tracking-tight">Deversator.VFR</span>
                    </div>
                    <p className="text-sm text-gray-600 font-medium">© 2026 Deversator Neural Networks. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
}
