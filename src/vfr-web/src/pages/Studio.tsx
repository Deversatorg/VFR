import { Suspense, useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';
import { Layers, Download, Maximize, Cpu, Rotate3D, Upload } from 'lucide-react';
import AvatarViewer from '../components/3d/AvatarViewer';
import { profileClient, avatarClient } from '../api/apiClients';
import { useNavigate } from 'react-router-dom';

export default function Studio() {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [modelLoading, setModelLoading] = useState(true);
    const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [statusMessage, setStatusMessage] = useState('Compiling Mesh');
    const navigate = useNavigate();

    // Fetch parametric profile and generate baseline avatar
    useEffect(() => {
        const loadBaselineAvatar = async () => {
            try {
                // 1. Fetch user physical profile
                setStatusMessage('Fetching Biometrics...');
                const profileRes = await profileClient.get('/api/v1/profiles/me');
                const profile = profileRes.data;

                // 2. Request parametric 3D generation
                setStatusMessage('Generating Neural Avatar...');
                const generateRes = await avatarClient.post('/api/v1/avatar/generate-from-profile', {
                    height: profile.height,
                    weight: profile.weight,
                    body_type: profile.bodyType
                });

                const _taskId = generateRes.data.task_id;

                // 3. Poll for result
                const pollStatus = async () => {
                    try {
                        const statusRes = await avatarClient.get(`/api/v1/avatar/status/${_taskId}`);
                        const data = statusRes.data;

                        if (data.status === 'SUCCESS') {
                            const baseUrl = import.meta.env.VITE_AI_ENGINE_API_URL || 'http://localhost:8000';
                            setAvatarUrl(`${baseUrl}${data.result.model_url}`);
                            setModelLoading(false);
                            setStatusMessage('Avatar Ready');
                        } else if (data.status === 'FAILURE') {
                            console.error('Task failed:', data.message);
                            setModelLoading(false);
                            setStatusMessage('Generation Failed');
                        } else {
                            if (data.message) {
                                setStatusMessage(data.message);
                            }
                            // Continue polling
                            setTimeout(pollStatus, 2000);
                        }
                    } catch (err) {
                        console.error('Error polling status:', err);
                        // Retry polling on temporary network errors
                        setTimeout(pollStatus, 3000);
                    }
                };

                pollStatus();

            } catch (error: any) {
                if (error.response?.status === 404) {
                    // No profile -> Force setup
                    navigate('/setup');
                } else {
                    console.error('Failed to generate baseline avatar', error);
                    setModelLoading(false);
                }
            }
        };

        loadBaselineAvatar();
    }, [navigate]);

    const handleUploadClick = () => {
        setIsGenerating(true);
        // Mock generation for photos
        setTimeout(() => {
            setAvatarUrl('mock_url');
            setIsGenerating(false);
        }, 3000);
    };

    return (
        <div className={`relative flex pt-[20px] pb-6 px-6 sm:px-8 gap-6 animate-in fade-in duration-700 ${isFullscreen ? 'fixed inset-0 z-50 bg-[#050505] p-0' : 'w-full h-full'}`}>

            {/* Left Sidebar - Studio Controls (Hidden in Fullscreen) */}
            {!isFullscreen && (
                <div className="w-[300px] flex flex-col gap-4">
                    <div className="p-6 rounded-[2rem] bg-[#0a0a0a]/80 border border-white/[0.06] backdrop-blur-xl shadow-2xl flex-shrink-0 animate-in slide-in-from-left-4">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20 flex items-center justify-center shadow-inner">
                                <Layers className="w-5 h-5 text-primary" />
                            </div>
                            <div>
                                <h2 className="text-white font-semibold tracking-tight">Avatar Controls</h2>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                    <span className="relative flex h-1.5 w-1.5">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                                    </span>
                                    <p className="text-[10px] text-gray-400 uppercase tracking-widest font-medium">Neural Mesh v2.0</p>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-5">
                            <div className="space-y-2">
                                <div className="flex justify-between items-end">
                                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Topological Density</span>
                                    <span className="text-[10px] text-primary font-mono tracking-widest">HIGH / 4M POLY</span>
                                </div>
                                <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div className="w-4/5 h-full bg-primary rounded-full" />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between items-end">
                                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Texture Sampling</span>
                                    <span className="text-[10px] text-blue-400 font-mono tracking-widest">4K / PBR</span>
                                </div>
                                <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div className="w-full h-full bg-blue-500 rounded-full" />
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={handleUploadClick}
                            disabled={isGenerating}
                            className="w-full mt-6 py-3 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/80 hover:to-blue-600/80 disabled:opacity-50 border border-transparent rounded-xl text-white font-medium shadow-lg transition-all flex items-center justify-center gap-2"
                        >
                            {isGenerating ? (
                                <>
                                    <Cpu className="w-5 h-5 animate-spin" />
                                    <span>Generating 3D Avatar...</span>
                                </>
                            ) : (
                                <>
                                    <Upload className="w-5 h-5" />
                                    <span>Upload Photo</span>
                                </>
                            )}
                        </button>

                        <button className="w-full mt-4 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2 group">
                            <Download className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                            <span className="text-gray-300 group-hover:text-white transition-colors">Export .OBJ Node</span>
                        </button>
                    </div>

                    <div className="flex-1 p-6 rounded-[2rem] bg-[#0a0a0a]/80 border border-white/[0.06] backdrop-blur-xl shadow-2xl flex flex-col items-center justify-center text-center animate-in slide-in-from-left-4 delay-75">
                        <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                            <Rotate3D className="w-5 h-5 text-gray-500" />
                        </div>
                        <h3 className="text-sm font-medium text-white mb-1">Wardrobe Engine</h3>
                        <p className="text-gray-500 text-xs leading-relaxed max-w-[200px]">Garment physics simulation will initialize once apparel is imported.</p>
                    </div>
                </div>
            )}

            {/* Main 3D Viewport Backdrop + Canvas */}
            <div className={`flex-1 relative bg-[#0a0a0a] border border-white/[0.06] shadow-2xl overflow-hidden flex items-center justify-center group transition-all duration-500 ${isFullscreen ? 'rounded-none border-0' : 'rounded-[2.5rem]'}`}>
                {/* Viewport Background Gradients */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-800/50 via-[#0a0a0a] to-[#050505] opacity-50" />

                {/* High Tech Grid Overlay */}
                <div className="absolute inset-0 opacity-20" style={{
                    backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
                    backgroundSize: '40px 40px',
                    backgroundPosition: 'center center'
                }} />

                {/* Loading State Overlay */}
                {modelLoading && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#0a0a0a]/80 backdrop-blur-sm transition-all duration-500">
                        <div className="w-16 h-16 relative flex items-center justify-center mb-4">
                            <div className="absolute inset-0 rounded-full border-t-2 border-primary animate-spin" />
                            <div className="absolute inset-2 rounded-full border-r-2 border-blue-500 animate-[spin_1.5s_linear_infinite]" />
                            <Cpu className="w-5 h-5 text-white/50" />
                        </div>
                        <p className="text-sm font-medium text-white tracking-widest uppercase">{statusMessage}</p>
                        <p className="text-[10px] text-primary font-mono mt-2">Loading neural weights...</p>
                    </div>
                )}

                <div className="absolute inset-0 z-10">
                    <Canvas
                        camera={{ position: [0, 1.2, 4], fov: 45 }}
                        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
                        dpr={[1, 2]}
                    >
                        <Suspense fallback={null}>
                            <Environment preset="city" />
                            <ambientLight intensity={0.4} />
                            <spotLight position={[5, 5, 5]} angle={0.2} penumbra={1} intensity={1} castShadow />
                            <directionalLight position={[-5, 5, -5]} intensity={0.5} />

                            <AvatarViewer modelUrl={avatarUrl} />

                            <ContactShadows position={[0, -1, 0]} opacity={0.4} scale={10} blur={2} far={4} />
                            <OrbitControls
                                enablePan={false}
                                enableZoom={true}
                                minDistance={2}
                                maxDistance={6}
                                maxPolarAngle={Math.PI / 2 + 0.1}
                                target={[0, 1, 0]}
                                autoRotate
                                autoRotateSpeed={0.5}
                            />
                        </Suspense>
                    </Canvas>
                </div>

                {/* Viewport UI Overlays */}
                <div className="absolute top-6 left-6 z-20 pointer-events-none">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/40 backdrop-blur-md border border-white/10">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-[10px] font-mono text-emerald-400 tracking-widest uppercase">Live Viewport</span>
                    </div>
                </div>

                <button
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="absolute bottom-6 right-6 z-20 w-12 h-12 bg-black/40 hover:bg-black/60 backdrop-blur-md rounded-2xl border border-white/10 flex items-center justify-center text-gray-400 hover:text-white transition-all duration-300 hover:scale-105 active:scale-95 shadow-lg"
                >
                    <Maximize className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}
