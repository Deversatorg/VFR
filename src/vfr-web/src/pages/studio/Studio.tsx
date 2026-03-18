import { useState, useEffect, useRef, useCallback } from 'react';
import { Maximize, Sparkles } from 'lucide-react';
import { profileClient, avatarClient } from '../../api/apiClients';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';

// New Modular Components
import CameraPresets from '../../components/studio/CameraPresets';
import StudioControls from '../../components/studio/StudioControls';
import Scene3D from '../../components/studio/Scene3D';

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

    const [chest, setChest]         = useState(0);
    const [waist, setWaist]         = useState(0);
    const [hip, setHip]             = useState(0);
    const [shoulder, setShoulder]   = useState(0);
    const [calf, setCalf]           = useState(0);
    const [armLength, setArmLength] = useState(0);
    const [torsoLength, setTorsoLength] = useState(0);
    const [legLength, setLegLength] = useState(0);

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

        const generatePromise = new Promise<void>(async (resolve, reject) => {
            let taskId: string;
            try {
                const res = await avatarClient.post('/api/v1/avatar/generate-from-profile', {
                    user_id: userId, height, weight, body_type: bodyType, gender,
                    chest, waist, hip, shoulder, calf,
                    arm_length: armLength,
                    torso_length: torsoLength,
                    leg_length: legLength,
                });
                taskId = res.data.task_id;
            } catch (err: any) {
                setGenStatus('error');
                const errMsg = 'Failed to queue avatar generation.';
                setGenError(errMsg);
                reject(new Error(errMsg));
                return;
            }

            pollCountRef.current = 0;
            pollRef.current = setInterval(async () => {
                pollCountRef.current += 1;
                if (pollCountRef.current > MAX_POLLS) {
                    stopPolling();
                    setGenStatus('error');
                    const errMsg = 'Generation timed out. Please try again.';
                    setGenError(errMsg);
                    reject(new Error(errMsg));
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
                        const fullUrl = raw.startsWith('http') ? raw : `${AVATAR_API_URL}${raw}`;
                        setAvatarUrl(fullUrl);
                        setGenProgress(100);
                        setGenStatus('success');
                        resolve();
                    } else if (status === 'FAILURE') {
                        stopPolling();
                        setGenStatus('error');
                        const errMsg = statusRes.data.message || 'Generation failed.';
                        setGenError(errMsg);
                        reject(new Error(errMsg));
                    }
                } catch {
                    // transient error — keep polling
                }
            }, POLL_INTERVAL_MS);
        });

        toast.promise(generatePromise, {
            loading: 'Compiling Neural Mesh...',
            success: 'Avatar generated successfully!',
            error: (err) => err.message || 'Failed to generate avatar.',
        });
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
                    <Scene3D
                        avatarUrl={avatarUrl}
                        gender={gender}
                        height={height}
                        weight={weight}
                        bodyType={bodyType}
                        animation={animation}
                        showShirt={selectedClothes.top !== null}
                        cameraResetTick={cameraResetTick}
                        cameraView={cameraView}
                        localHeight={localHeight}
                    />
                </div>

                {/* Generation progress bar (UI Overlay) */}
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
                <CameraPresets cameraView={cameraView} onSelectView={setCameraView} />

                <button
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="absolute top-6 left-6 z-20 w-10 h-10 bg-black/40 hover:bg-black/60 backdrop-blur-md rounded-xl border border-white/10 flex items-center justify-center text-gray-400 hover:text-white transition-all shadow-lg"
                >
                    <Maximize className="w-4 h-4" />
                </button>
            </div>

            {/* Control Panel Area */}
            {!isFullscreen && (
                <StudioControls
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    gender={gender}
                    setGender={setGender}
                    localHeight={localHeight}
                    setLocalHeight={setLocalHeight}
                    localWeight={localWeight}
                    setLocalWeight={setLocalWeight}
                    bodyType={bodyType}
                    setBodyType={setBodyType}
                    animation={animation}
                    setAnimation={setAnimation}
                    genStatus={genStatus}
                    genProgress={genProgress}
                    genError={genError}
                    handleGenerateAvatar={handleGenerateAvatar}
                    selectedClothes={selectedClothes}
                    handleClothingSelect={handleClothingSelect}
                    mockClothes={MOCK_CLOTHES}
                    chest={chest}
                    setChest={setChest}
                    waist={waist}
                    setWaist={setWaist}
                    hip={hip}
                    setHip={setHip}
                    shoulder={shoulder}
                    setShoulder={setShoulder}
                    calf={calf}
                    setCalf={setCalf}
                    armLength={armLength}
                    setArmLength={setArmLength}
                    torsoLength={torsoLength}
                    setTorsoLength={setTorsoLength}
                    legLength={legLength}
                    setLegLength={setLegLength}
                />
            )}
        </div>
    );
}
