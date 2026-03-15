import { Suspense, useState, useEffect, useRef, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';
import { Layers, Maximize, Cpu, Rotate3D, Upload, Shirt, Sparkles, AlertCircle } from 'lucide-react';
import AvatarViewer from '../components/3d/AvatarViewer';
import { profileClient, avatarClient } from '../api/apiClients';
import { useNavigate } from 'react-router-dom';

const AVATAR_API_URL = import.meta.env.VITE_AI_ENGINE_API_URL || 'http://localhost:8000';
const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 60; // 2 min timeout

type GenStatus = 'idle' | 'pending' | 'success' | 'error';

export default function Studio() {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const navigate = useNavigate();

    // Parametric controls state
    const [height, setHeight] = useState(170);
    const [weight, setWeight] = useState(70);
    const [bodyType, setBodyType] = useState('regular');
    const [gender, setGender] = useState<'male' | 'female'>('male');
    const [animation, setAnimation] = useState<'idle' | 'walk' | 'run' | 'jump' | 'tpose'>('idle');
    const [showShirt, setShowShirt] = useState(false);

    // Avatar generation state
    const [avatarUrl, setAvatarUrl]       = useState<string | null>(null);
    const [genStatus, setGenStatus]       = useState<GenStatus>('idle');
    const [genProgress, setGenProgress]   = useState(0);
    const [genError, setGenError]         = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollCountRef = useRef(0);

    const stopPolling = useCallback(() => {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        pollCountRef.current = 0;
    }, []);

    // Fetch initial parametric profile from the backend
    useEffect(() => {
        const loadProfile = async () => {
            try {
                const profileRes = await profileClient.get('/api/v1/profiles/me');
                if (profileRes.data) {
                    setHeight(profileRes.data.height || 170);
                    setWeight(profileRes.data.weight || 70);
                    setBodyType((profileRes.data.bodyType || 'regular').toLowerCase());
                }
            } catch (error: any) {
                if (error.response?.status === 404) { navigate('/setup'); }
                console.error('Failed to load profile', error);
            }
        };
        loadProfile();
    }, [navigate]);

    // Reset generated avatar when gender changes
    useEffect(() => { setAvatarUrl(null); }, [gender]);

    // Cleanup polling on unmount
    useEffect(() => () => stopPolling(), [stopPolling]);

    const handleGenerateAvatar = async () => {
        setGenStatus('pending');
        setGenProgress(5);
        setGenError(null);
        stopPolling();

        let taskId: string;
        try {
            const res = await avatarClient.post('/api/v1/avatar/generate-from-profile', {
                height, weight, body_type: bodyType, gender,
            });
            taskId = res.data.task_id;
        } catch (err: any) {
            setGenStatus('error');
            setGenError('Failed to queue avatar generation.');
            return;
        }

        pollCountRef.current = 0;
        pollRef.current = setInterval(async () => {
            pollCountRef.current += 1;
            if (pollCountRef.current > MAX_POLLS) {
                stopPolling();
                setGenStatus('error');
                setGenError('Generation timed out. Please try again.');
                return;
            }

            try {
                const statusRes = await avatarClient.get(`/api/v1/avatar/status/${taskId}`);
                const { status, progress, result } = statusRes.data;

                if (status === 'PROGRESS' || status === 'STARTED') {
                    setGenProgress(Math.max(10, Math.min(90, progress ?? 50)));
                } else if (status === 'SUCCESS') {
                    stopPolling();
                    const raw = result.model_url as string;
                    // Pipeline returns a full https:// S3 URL; fallback returns a relative /models/... path
                    const fullUrl = raw.startsWith('http') ? raw : `${AVATAR_API_URL}${raw}`;
                    setAvatarUrl(fullUrl);
                    setGenProgress(100);
                    setGenStatus('success');
                } else if (status === 'FAILURE') {
                    stopPolling();
                    setGenStatus('error');
                    setGenError(statusRes.data.message || 'Generation failed.');
                }
            } catch {
                // transient error — keep polling
            }
        }, POLL_INTERVAL_MS);
    };

    const handleUploadClick = () => {
        // Photo upload — separate future feature; keep as-is
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

                        <div className="space-y-6">
                            {/* Gender Selector */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Gender Base</span>
                                <div className="flex gap-2 mt-2">
                                    {(['male', 'female'] as const).map(type => (
                                        <button
                                            key={type}
                                            onClick={() => setGender(type)}
                                            className={`flex-1 py-1.5 rounded-lg text-[10px] font-medium transition-all ${gender === type
                                                ? 'bg-primary/20 text-primary border border-primary/50'
                                                : 'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10'
                                                }`}
                                        >
                                            {type.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            {/* Height Slider */}
                            <div className="space-y-2">
                                <div className="flex justify-between items-end">
                                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Height</span>
                                    <span className="text-[11px] text-white font-mono">{height} cm</span>
                                </div>
                                <input
                                    type="range"
                                    min="140"
                                    max="220"
                                    value={height}
                                    onChange={(e) => setHeight(Number(e.target.value))}
                                    className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-primary"
                                />
                            </div>

                            {/* Weight Slider */}
                            <div className="space-y-2">
                                <div className="flex justify-between items-end">
                                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Weight</span>
                                    <span className="text-[11px] text-white font-mono">{weight} kg</span>
                                </div>
                                <input
                                    type="range"
                                    min="40"
                                    max="150"
                                    value={weight}
                                    onChange={(e) => setWeight(Number(e.target.value))}
                                    className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-blue-500"
                                />
                            </div>

                            {/* Body Type Selector */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Body Type</span>
                                <div className="flex gap-2 mt-2">
                                    {['slim', 'regular', 'athletic', 'curvy'].map(type => (
                                        <button
                                            key={type}
                                            onClick={() => setBodyType(type)}
                                            className={`flex-1 py-1.5 rounded-lg text-[10px] font-medium transition-all ${bodyType === type
                                                ? 'bg-primary/20 text-primary border border-primary/50'
                                                : 'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10'
                                                }`}
                                        >
                                            {type.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Animation Selector */}
                            <div className="space-y-2 mt-6">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Animation State</span>
                                <div className="grid grid-cols-3 gap-2 mt-2">
                                    {['idle', 'walk', 'run', 'jump', 'tpose'].map(anim => (
                                        <button
                                            key={anim}
                                            onClick={() => setAnimation(anim as any)}
                                            className={`py-1.5 rounded-lg text-[10px] items-center justify-center flex font-medium transition-all ${animation === anim
                                                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                                                : 'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10'
                                                }`}
                                        >
                                            {anim.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Wardrobe Toggles */}
                            <div className="space-y-2 mt-4">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Wardrobe</span>
                                <div className="grid grid-cols-2 gap-2 mt-2">
                                    <button
                                        onClick={() => setShowShirt(s => !s)}
                                        className={`py-2 rounded-lg text-[10px] flex items-center justify-center gap-1.5 font-medium transition-all ${showShirt
                                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                                            : 'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10'
                                            }`}
                                    >
                                        <Shirt className="w-3 h-3" />
                                        T-SHIRT
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Generate Avatar Button */}
                        <button
                            onClick={handleGenerateAvatar}
                            disabled={genStatus === 'pending'}
                            className="w-full mt-6 py-3 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/80 hover:to-blue-600/80 disabled:opacity-50 border border-transparent rounded-xl text-white font-medium shadow-lg transition-all flex items-center justify-center gap-2"
                        >
                            {genStatus === 'pending' ? (
                                <>
                                    <Cpu className="w-5 h-5 animate-spin" />
                                    <span>Generating... {genProgress}%</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-5 h-5" />
                                    <span>{genStatus === 'success' ? 'Regenerate Avatar' : 'Generate Avatar'}</span>
                                </>
                            )}
                        </button>

                        {/* Error message */}
                        {genStatus === 'error' && genError && (
                            <div className="mt-3 flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                                <p className="text-[11px] text-red-400 leading-relaxed">{genError}</p>
                            </div>
                        )}

                        {/* Upload Photo (secondary) */}
                        <button
                            onClick={handleUploadClick}
                            className="w-full mt-2 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-gray-400 text-[11px] font-medium transition-all flex items-center justify-center gap-2"
                        >
                            <Upload className="w-4 h-4" />
                            <span>Upload Photo (coming soon)</span>
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
            )
            }

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

                            <AvatarViewer
                                key={avatarUrl ?? gender}
                                modelUrl={avatarUrl ?? (gender === 'male' ? '/models/Male.glb' : '/models/Female.glb')}
                                height={height}
                                weight={weight}
                                bodyType={bodyType}
                                gender={gender}
                                animation={animation}
                                showShirt={showShirt}
                            />

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

                {/* Generation progress bar */}
                {genStatus === 'pending' && (
                    <div className="absolute bottom-0 left-0 right-0 z-30 h-[3px] bg-white/5">
                        <div
                            className="h-full bg-gradient-to-r from-primary to-blue-500 transition-all duration-700"
                            style={{ width: `${genProgress}%` }}
                        />
                    </div>
                )}

                {/* Success badge */}
                {genStatus === 'success' && (
                    <div className="absolute top-6 right-16 z-20">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 backdrop-blur-md border border-emerald-500/30">
                            <Sparkles className="w-3 h-3 text-emerald-400" />
                            <span className="text-[10px] font-mono text-emerald-400 tracking-widest uppercase">AI Generated</span>
                        </div>
                    </div>
                )}

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
        </div >
    );
}
