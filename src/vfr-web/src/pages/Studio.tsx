import { Suspense, useState, useEffect, useRef, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';
import { Maximize, Cpu, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';
import AvatarViewer from '../components/3d/AvatarViewer';
import CameraController from '../components/3d/CameraController';
import { profileClient, avatarClient } from '../api/apiClients';
import { useNavigate } from 'react-router-dom';

const AVATAR_API_URL = import.meta.env.VITE_AI_ENGINE_API_URL || 'http://localhost:8000';
const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 60; // 2 min timeout

const MOCK_CLOTHES = [
    { id: 't1', type: 'top', name: 'Classic White T-Shirt', color: '#ffffff' },
    { id: 't2', type: 'top', name: 'Black Hoodie', color: '#1a1a1a' },
    { id: 'b1', type: 'bottom', name: 'Blue Jeans', color: '#1e3a8a' },
    { id: 'b2', type: 'bottom', name: 'Cargo Pants', color: '#4b5563' },
];

type GenStatus = 'idle' | 'pending' | 'success' | 'error';

export default function Studio() {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const navigate = useNavigate();

    // Parametric controls state
    const [height, setHeight] = useState(170);
    const [weight, setWeight] = useState(70);
    
    // Local state for performant slider updates before triggering a fetch/render
    const [localHeight, setLocalHeight] = useState(170);
    const [localWeight, setLocalWeight] = useState(70);
    const [bodyType, setBodyType] = useState('regular');
    const [gender, setGender] = useState<'male' | 'female'>('male');
    const [animation, setAnimation] = useState<'idle' | 'walk' | 'run' | 'jump' | 'tpose'>('idle');
    const [userId, setUserId] = useState<string>('default_user');

    // UI State for Tabs & Wardrobe
    const [activeTab, setActiveTab] = useState<'body' | 'wardrobe'>('body');
    const [selectedClothes, setSelectedClothes] = useState<{ top: string | null, bottom: string | null }>({ top: null, bottom: null });

    const handleClothingSelect = (item: any) => {
        setSelectedClothes(prev => {
            const isCurrentlySelected = prev[item.type as keyof typeof prev] === item.id;
            return {
                ...prev,
                [item.type]: isCurrentlySelected ? null : item.id
            };
        });
    };

    // Avatar generation state
    const [avatarUrl, setAvatarUrl]       = useState<string | null>(null);
    const [genStatus, setGenStatus]       = useState<GenStatus>('idle');
    const [genProgress, setGenProgress]   = useState(0);
    const [genError, setGenError]         = useState<string | null>(null);
    const [cameraResetTick, setCameraResetTick] = useState(0);
    const [cameraView, setCameraView] = useState<'front' | 'back' | 'left' | 'right' | 'face'>('front');
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollCountRef = useRef(0);

    const stopPolling = useCallback(() => {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        pollCountRef.current = 0;
    }, []);

    const handleResetCamera = useCallback(() => {
        setCameraResetTick(prev => prev + 1);
    }, []);

    // Fetch initial parametric profile from the backend
    useEffect(() => {
        const loadProfile = async () => {
            try {
                const profileRes = await profileClient.get('/api/v1/profiles/me');
                if (profileRes.data) {
                    setUserId(profileRes.data.userId || profileRes.data.id || 'default_user');
                    setHeight(profileRes.data.height || 170);
                    setLocalHeight(profileRes.data.height || 170);
                    setWeight(profileRes.data.weight || 70);
                    setLocalWeight(profileRes.data.weight || 70);
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

    // Auto-frame camera when a new model loads
    useEffect(() => { handleResetCamera(); }, [avatarUrl, gender, handleResetCamera]);

    // Cleanup polling on unmount
    useEffect(() => () => stopPolling(), [stopPolling]);

    // --- Debounce Logic for Sliders ---
    useEffect(() => {
        if (localHeight === height) return;
        const handler = setTimeout(() => {
            setHeight(localHeight);
        }, 750);
        return () => clearTimeout(handler);
    }, [localHeight, height]);

    useEffect(() => {
        if (localWeight === weight) return;
        const handler = setTimeout(() => {
            setWeight(localWeight);
        }, 750);
        return () => clearTimeout(handler);
    }, [localWeight, weight]);
    // ----------------------------------

    const handleGenerateAvatar = async () => {
        setGenStatus('pending');
        setGenProgress(5);
        setGenError(null);
        stopPolling();

        let taskId: string;
        try {
            const res = await avatarClient.post('/api/v1/avatar/generate-from-profile', {
                user_id: userId, height, weight, body_type: bodyType, gender,
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

    return (
        <div className={`flex flex-col md:flex-row h-screen w-full overflow-hidden bg-[#050505] animate-in fade-in duration-700 ${isFullscreen ? 'fixed inset-0 z-50 p-0' : 'pt-20'}`}>

            {/* Main 3D Viewport Backdrop + Canvas */}
            <div className={`w-full relative bg-[#0a0a0a] transition-all duration-500 overflow-hidden ${isFullscreen ? 'h-full md:w-full border-0 z-50' : 'h-[60vh] md:h-full md:w-2/3 border-b md:border-b-0 md:border-r border-white/[0.06] shadow-2xl'}`}>
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
                                showShirt={selectedClothes.top !== null}
                            />

                            <CameraController avatarHeight={localHeight / 100} trigger={cameraResetTick} view={cameraView} />
                            
                            <ContactShadows position={[0, -1, 0]} opacity={0.4} scale={10} blur={2} far={4} />
                            <OrbitControls
                                makeDefault
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
                            style={{ width: `${Math.max(5, genProgress)}%` }}
                        />
                    </div>
                )}

                {/* Success badge */}
                {genStatus === 'success' && (
                    <div className="absolute top-6 right-6 z-20">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 backdrop-blur-md border border-emerald-500/30">
                            <Sparkles className="w-3 h-3 text-emerald-400" />
                            <span className="text-[10px] font-mono text-emerald-400 tracking-widest uppercase">AI Generated</span>
                        </div>
                    </div>
                )}

                {/* Floating Camera Presets Toolbar */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 flex items-center p-1 border border-white/10 bg-black/50 backdrop-blur-xl rounded-2xl shadow-2xl">
                    {(['front', 'back', 'left', 'right', 'face'] as const).map(v => (
                        <button
                            key={v}
                            onClick={() => setCameraView(v)}
                            className={`px-3 py-1.5 md:px-4 md:py-2 rounded-xl text-[9px] md:text-[10px] font-bold uppercase tracking-widest transition-all ${
                                cameraView === v 
                                    ? 'bg-primary text-white shadow-lg shadow-primary/20' 
                                    : 'text-gray-400 hover:text-white hover:bg-white/10'
                            }`}
                        >
                            {v}
                        </button>
                    ))}
                </div>

                <button
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="absolute top-6 left-6 z-20 w-10 h-10 bg-black/40 hover:bg-black/60 backdrop-blur-md rounded-xl border border-white/10 flex items-center justify-center text-gray-400 hover:text-white transition-all shadow-lg"
                >
                    <Maximize className="w-4 h-4" />
                </button>
            </div>

            {/* Control Panel Area (Bottom Sheet on Mobile) */}
            {!isFullscreen && (
                <div className="w-full md:w-1/3 h-[40vh] md:h-full bg-[#0a0a0a] shadow-[0_-20px_40px_rgba(0,0,0,0.5)] md:shadow-none z-20 overflow-y-auto p-4 md:p-6 md:rounded-none flex flex-col gap-6 scrollbar-hide pb-24 md:pb-6 relative rounded-t-2xl">
                    
                    {/* Tabs */}
                    <div className="flex bg-[#111111] p-1 rounded-xl border border-white/5 shrink-0 sticky top-0 z-10">
                        <button
                            onClick={() => setActiveTab('body')}
                            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${activeTab === 'body' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            My Body
                        </button>
                        <button
                            onClick={() => setActiveTab('wardrobe')}
                            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${activeTab === 'wardrobe' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            Wardrobe
                        </button>
                    </div>

                    {/* Body Tab Content */}
                    {activeTab === 'body' && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                            {/* Gender Selector */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Gender Base</span>
                                <div className="flex gap-2">
                                    {(['male', 'female'] as const).map(type => (
                                        <button
                                            key={type}
                                            onClick={() => setGender(type)}
                                            className={`flex-1 py-2 rounded-xl text-xs font-medium transition-all ${gender === type
                                                ? 'bg-primary/20 text-primary border border-primary/50'
                                                : 'bg-[#111111] text-gray-400 border border-white/5 hover:bg-white/5'
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
                                    <span className="text-sm text-white font-mono">{localHeight} cm</span>
                                </div>
                                <input
                                    type="range"
                                    min="140"
                                    max="220"
                                    value={localHeight}
                                    onChange={(e) => setLocalHeight(Number(e.target.value))}
                                    className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-primary"
                                />
                            </div>

                            {/* Weight Slider */}
                            <div className="space-y-2">
                                <div className="flex justify-between items-end">
                                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Weight</span>
                                    <span className="text-sm text-white font-mono">{localWeight} kg</span>
                                </div>
                                <input
                                    type="range"
                                    min="40"
                                    max="150"
                                    value={localWeight}
                                    onChange={(e) => setLocalWeight(Number(e.target.value))}
                                    className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-blue-500"
                                />
                            </div>

                            {/* Body Type Selector */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Body Type</span>
                                <div className="grid grid-cols-2 gap-2">
                                    {['slim', 'regular', 'athletic', 'curvy'].map(type => (
                                        <button
                                            key={type}
                                            onClick={() => setBodyType(type)}
                                            className={`py-2 rounded-xl text-xs font-medium transition-all ${bodyType === type
                                                ? 'bg-primary/20 text-primary border border-primary/50'
                                                : 'bg-[#111111] text-gray-400 border border-white/5 hover:bg-white/5'
                                                }`}
                                        >
                                            {type.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Animation Selector */}
                            <div className="space-y-2">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Animation State</span>
                                <div className="grid grid-cols-3 gap-2">
                                    {['idle', 'walk', 'run', 'jump', 'tpose'].map(anim => (
                                        <button
                                            key={anim}
                                            onClick={() => setAnimation(anim as any)}
                                            className={`py-2 rounded-xl text-[10px] items-center justify-center flex font-medium transition-all ${animation === anim
                                                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                                                : 'bg-[#111111] text-gray-400 border border-white/5 hover:bg-white/5'
                                                }`}
                                        >
                                            {anim.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Generate Avatar Button */}
                            <button
                                onClick={handleGenerateAvatar}
                                disabled={genStatus === 'pending'}
                                className="w-full mt-2 py-3.5 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/80 hover:to-blue-600/80 disabled:opacity-50 rounded-xl text-white font-semibold shadow-lg transition-all flex items-center justify-center gap-2"
                            >
                                {genStatus === 'pending' ? (
                                    <>
                                        <Cpu className="w-5 h-5 animate-spin" />
                                        <span>Generating... {Math.max(5, genProgress)}%</span>
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
                                <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                                    <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-red-400 leading-relaxed">{genError}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Wardrobe Tab Content */}
                    {activeTab === 'wardrobe' && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-semibold text-white">Apparel Library</span>
                                <span className="text-xs text-gray-500">{MOCK_CLOTHES.length} Items</span>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-3 pb-8">
                                {MOCK_CLOTHES.map(item => {
                                    const isSelected = selectedClothes.top === item.id || selectedClothes.bottom === item.id;
                                    return (
                                        <div
                                            key={item.id}
                                            onClick={() => handleClothingSelect(item)}
                                            className={`relative cursor-pointer rounded-2xl overflow-hidden transition-all duration-200 border-2 ${
                                                isSelected ? 'border-primary shadow-[0_0_15px_rgba(19,91,236,0.3)] hover:border-primary' : 'border-[#1a1a1a] hover:border-white/20'
                                            }`}
                                        >
                                            <div className="aspect-[4/5] bg-[#111111] flex flex-col p-3">
                                                <div 
                                                    className="flex-1 rounded-xl mb-3 shadow-inner opacity-80" 
                                                    style={{ backgroundColor: item.color }}
                                                />
                                                <div className="flex justify-between items-end">
                                                    <div>
                                                        <p className="text-xs font-medium text-white line-clamp-1">{item.name}</p>
                                                        <p className="text-[10px] text-gray-500 capitalize mt-0.5">{item.type}</p>
                                                    </div>
                                                    {isSelected && (
                                                        <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
