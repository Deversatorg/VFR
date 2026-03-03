import { Suspense, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment, ContactShadows } from '@react-three/drei';
import { profileClient } from '../api/apiClients';
import { useNavigate } from 'react-router-dom';
import { LogOut, Activity, Settings, Maximize, User } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

function Model({ url }: { url: string }) {
    const { scene } = useGLTF(url);
    useEffect(() => {
        scene.traverse((child: any) => {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
            }
        });
    }, [scene]);
    return <primitive object={scene} scale={2} position={[0, -1.5, 0]} />;
}

export default function AvatarViewer() {
    const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const logout = useAuthStore(state => state.logout);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchAvatar = async () => {
            try {
                const response = await profileClient.get('/api/profile/my-avatar');
                if (response.data.avatarUrl) {
                    setAvatarUrl(`${profileClient.defaults.baseURL}${response.data.avatarUrl}`);
                } else {
                    navigate('/setup');
                }
            } catch (err) {
                setError('Failed to load avatar. Have you completed the setup?');
            } finally {
                setLoading(false);
            }
        };
        fetchAvatar();
    }, [navigate]);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-[#050505] text-white">
                <div className="relative w-24 h-24 mb-6 flex items-center justify-center">
                    <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
                    <svg className="animate-spin w-12 h-12 text-primary relative z-10" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                </div>
                <h3 className="text-xl font-medium tracking-wide">Initializing Studio Engine</h3>
                <p className="text-gray-500 text-sm mt-2">Loading neural assets...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#050505] p-4">
                <div className="max-w-md w-full backdrop-blur-3xl bg-[#0a0a0a]/80 border border-white/10 p-8 rounded-3xl text-center shadow-2xl">
                    <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-2xl mx-auto mb-6 flex items-center justify-center border border-red-500/20">
                        <Activity size={24} />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">Initialization Failed</h3>
                    <p className="text-gray-400 text-sm mb-8">{error}</p>
                    <button onClick={() => navigate('/setup')} className="w-full py-4 bg-white/5 hover:bg-white/10 text-white rounded-xl transition-all font-medium border border-white/10">Return to Setup</button>
                </div>
            </div>
        );
    }

    return (
        <div className="relative w-screen h-screen bg-[#050505] overflow-hidden font-sans">
            {/* Top Navigation Bar */}
            <div className="absolute top-0 left-0 w-full z-20">
                <div className="bg-gradient-to-b from-[#050505] via-[#050505]/80 to-transparent pt-6 pb-12 px-6 sm:px-10 flex justify-between items-start pointer-events-none">
                    <div className="flex items-center gap-4 pointer-events-auto">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-blue-800 flex items-center justify-center shadow-lg shadow-primary/30 border border-white/10">
                            <Activity className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold text-white tracking-wide leading-tight">VFR Studio</h1>
                            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">Neural Engine Active</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3 pointer-events-auto">
                        <button className="w-10 h-10 flex items-center justify-center bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-xl transition-all backdrop-blur-md border border-white/10 shadow-sm hidden sm:flex">
                            <Settings size={18} />
                        </button>
                        <button className="w-10 h-10 flex items-center justify-center bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-xl transition-all backdrop-blur-md border border-white/10 shadow-sm hidden sm:flex">
                            <Maximize size={18} />
                        </button>
                        <button onClick={handleLogout} className="flex items-center gap-2 px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-xl transition-all backdrop-blur-md border border-red-500/20 font-medium text-sm">
                            <LogOut size={16} /> <span className="hidden sm:inline">Disconnect</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Floating Action Menu (Left) */}
            <div className="absolute left-6 top-1/2 -translate-y-1/2 z-20 flex flex-col gap-3 pointer-events-auto hidden md:flex">
                <div className="p-1.5 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl flex flex-col gap-1 shadow-2xl">
                    <button className="p-3 text-primary bg-primary/10 rounded-xl hover:bg-primary/20 transition-colors">
                        <User size={20} />
                    </button>
                    <button className="p-3 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path><line x1="16" y1="8" x2="2" y2="22"></line><line x1="17.5" y1="15" x2="9" y2="15"></line></svg>
                    </button>
                    <button className="p-3 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path></svg>
                    </button>
                </div>
            </div>

            {/* 3D Canvas */}
            <div className="absolute inset-0 z-0">
                <Canvas shadows camera={{ position: [0, 1.2, 4.5], fov: 40 }}>
                    <color attach="background" args={['#050505']} />

                    <ambientLight intensity={0.6} />
                    <directionalLight
                        position={[5, 8, 5]}
                        castShadow
                        intensity={1.2}
                        shadow-mapSize={[2048, 2048]}
                        shadow-bias={-0.0001}
                    />
                    <directionalLight position={[-5, 5, -5]} intensity={0.5} color="#135bec" />
                    <directionalLight position={[0, 0, 5]} intensity={0.3} color="#ffffff" />

                    <Environment preset="city" />

                    <Suspense fallback={null}>
                        {avatarUrl && <Model url={avatarUrl} />}
                        {/* Floor Shadow */}
                        <ContactShadows position={[0, -1.5, 0]} opacity={0.6} scale={15} blur={2.5} far={4} color="#000000" />

                        {/* Decorative Grid Floor */}
                        <gridHelper args={[20, 20, '#135bec', '#ffffff']} position={[0, -1.51, 0]} material-opacity={0.05} material-transparent />
                    </Suspense>

                    <OrbitControls
                        enablePan={false}
                        enableZoom={true}
                        minDistance={2}
                        maxDistance={6}
                        maxPolarAngle={Math.PI / 1.6}
                        minPolarAngle={Math.PI / 4}
                        autoRotate={true}
                        autoRotateSpeed={0.3}
                        target={[0, 0, 0]}
                    />
                </Canvas>
            </div>

            {/* Bottom Status Bar */}
            <div className="absolute bottom-0 left-0 w-full z-10 pointer-events-none">
                <div className="bg-gradient-to-t from-[#050505] via-[#050505]/50 to-transparent pt-12 pb-6 px-10 flex justify-between items-end">
                    <div className="flex gap-6 items-center">
                        <div className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                            <span className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">Engine Online</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                            <span className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">Sync Complete</span>
                        </div>
                    </div>
                    <p className="text-white/20 text-xs tracking-widest uppercase hidden sm:block">Drag to rotate • Scroll to zoom</p>
                </div>
            </div>
        </div>
    );
}

useGLTF.preload('/sample-data/avatar.glb');
