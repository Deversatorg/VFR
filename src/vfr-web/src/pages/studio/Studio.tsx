import { useState, useEffect, useRef, useCallback, useEffectEvent } from 'react';
import { Maximize, Sparkles } from 'lucide-react';
import { profileClient, avatarClient } from '../../api/apiClients';
import { unstable_usePrompt as usePrompt, useBeforeUnload, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { createLogger } from '../../lib/logger';

// New Modular Components
import CameraPresets from '../../components/studio/CameraPresets';
import StudioControls from '../../components/studio/StudioControls';
import Scene3D from '../../components/studio/Scene3D';
import {
    EMPTY_AUTO_MEASUREMENTS,
    EMPTY_MANUAL_MEASUREMENTS,
    buildStudioDraftFingerprintSource,
    createStudioDraftFingerprint,
    mapAutoMeasurements,
    mapManualMeasurements,
    type AutoMeasurementsState,
    type ManualMeasurementsState,
    type StudioDraftSnapshot,
    type StudioGeneratedAvatarState,
    type StudioProfileResponse,
    type ViewportMode,
} from '../../components/studio/studioState';

const AVATAR_API_URL = import.meta.env.VITE_AI_ENGINE_API_URL || 'http://localhost:8000';
const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 60; // 2 min timeout
const logger = createLogger('VFR.Web.Studio');

const MOCK_CLOTHES = [
    {
        id: 't1',
        type: 'top',
        name: 'Classic White T-Shirt',
        color: '#f5f5f5',
        previewUrl: '/models/garments/t-shirt.glb',
        previewTint: '#f5f5f5',
        supported: true,
        previewNote: 'Live preview available',
    },
    {
        id: 't2',
        type: 'top',
        name: 'Black Hoodie',
        color: '#1a1a1a',
        previewUrl: '/models/garments/t-shirt.glb',
        previewTint: '#18181b',
        supported: true,
        previewNote: 'Using current top preview mesh',
    },
    {
        id: 'b1',
        type: 'bottom',
        name: 'Blue Jeans',
        color: '#1e3a8a',
        previewUrl: null,
        previewTint: null,
        supported: false,
        previewNote: 'Bottom garment preview is next',
    },
    {
        id: 'b2',
        type: 'bottom',
        name: 'Cargo Pants',
        color: '#4b5563',
        previewUrl: null,
        previewTint: null,
        supported: false,
        previewNote: 'Bottom garment preview is next',
    },
] as const;

type GenStatus = 'idle' | 'pending' | 'success' | 'error';
type CompositionPresetKey = 'lean' | 'athletic' | 'average' | 'soft';

const DEFAULT_MUSCULARITY_BY_BODY_TYPE: Record<string, number> = {
    slim: 35,
    regular: 50,
    athletic: 72,
    curvy: 45,
};

const DEFAULT_BODY_FAT_BY_PROFILE: Record<'male' | 'female', Record<string, number>> = {
    male: {
        slim: 12,
        regular: 18,
        athletic: 14,
        curvy: 24,
    },
    female: {
        slim: 20,
        regular: 28,
        athletic: 23,
        curvy: 34,
    },
};

const toNullableMeasurement = (value: number) => (value > 0 ? value : null);

const toBodyTypeEnum = (value: string) =>
    value ? `${value.charAt(0).toUpperCase()}${value.slice(1).toLowerCase()}` : 'Regular';

const toGenderEnum = (value: 'male' | 'female') =>
    value === 'female' ? 'Female' : 'Male';

const getDefaultMuscularity = (bodyType: string) =>
    DEFAULT_MUSCULARITY_BY_BODY_TYPE[bodyType] ?? DEFAULT_MUSCULARITY_BY_BODY_TYPE.regular;

const getDefaultBodyFatPercentage = (gender: 'male' | 'female', bodyType: string) =>
    DEFAULT_BODY_FAT_BY_PROFILE[gender][bodyType] ?? DEFAULT_BODY_FAT_BY_PROFILE[gender].regular;

const BODY_TYPE_BY_COMPOSITION_PRESET: Record<CompositionPresetKey, string> = {
    lean: 'slim',
    athletic: 'athletic',
    average: 'regular',
    soft: 'curvy',
};

const getCompositionPresets = (gender: 'male' | 'female') =>
    gender === 'female'
        ? [
            { key: 'lean' as const, muscularity: 32, bodyFatPercentage: 18 },
            { key: 'athletic' as const, muscularity: 58, bodyFatPercentage: 22 },
            { key: 'average' as const, muscularity: 44, bodyFatPercentage: 28 },
            { key: 'soft' as const, muscularity: 30, bodyFatPercentage: 34 },
        ]
        : [
            { key: 'lean' as const, muscularity: 42, bodyFatPercentage: 11 },
            { key: 'athletic' as const, muscularity: 72, bodyFatPercentage: 14 },
            { key: 'average' as const, muscularity: 52, bodyFatPercentage: 19 },
            { key: 'soft' as const, muscularity: 36, bodyFatPercentage: 26 },
        ];

const resolveBodyTypeFromComposition = (
    gender: 'male' | 'female',
    muscularity: number,
    bodyFatPercentage: number,
) => {
    const closestPreset = getCompositionPresets(gender).reduce((closest, preset) => {
        const currentDistance =
            Math.abs(preset.muscularity - muscularity) +
            Math.abs(preset.bodyFatPercentage - bodyFatPercentage);
        const closestDistance =
            Math.abs(closest.muscularity - muscularity) +
            Math.abs(closest.bodyFatPercentage - bodyFatPercentage);

        return currentDistance < closestDistance ? preset : closest;
    });

    return BODY_TYPE_BY_COMPOSITION_PRESET[closestPreset.key];
};

export default function Studio() {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const navigate = useNavigate();

    const [height, setHeight] = useState(170);
    const [weight, setWeight] = useState(70);
    const [bodyType, setBodyType] = useState('regular');
    const [gender, setGender] = useState<'male' | 'female'>('male');
    const [muscularity, setMuscularity] = useState(getDefaultMuscularity('regular'));
    const [bodyFatPercentage, setBodyFatPercentage] = useState(getDefaultBodyFatPercentage('male', 'regular'));
    const [animation, setAnimation] = useState<'idle' | 'walk' | 'run' | 'jump' | 'tpose'>('idle');
    const [userId, setUserId] = useState<string>('default_user');

    const [manualMeasurements, setManualMeasurements] = useState<ManualMeasurementsState>(EMPTY_MANUAL_MEASUREMENTS);
    const [autoMeasurements, setAutoMeasurements] = useState<AutoMeasurementsState>(EMPTY_AUTO_MEASUREMENTS);
    const [savedDraft, setSavedDraft] = useState<StudioDraftSnapshot | null>(null);
    const [savedDraftHash, setSavedDraftHash] = useState('');
    const [currentDraftHash, setCurrentDraftHash] = useState('');
    const [generatedAvatar, setGeneratedAvatar] = useState<StudioGeneratedAvatarState>({
        modelUrl: null,
        generatedAt: null,
        inputHash: null,
        isCurrent: false,
    });
    const [viewportMode, setViewportMode] = useState<ViewportMode>('preview');
    const [saveStatus, setSaveStatus] = useState<'idle' | 'pending' | 'success' | 'error'>('idle');
    const [saveError, setSaveError] = useState<string | null>(null);
    const [isProfileLoaded, setIsProfileLoaded] = useState(false);

    const [activeTab, setActiveTab] = useState<'body' | 'wardrobe'>('body');
    const [selectedClothes, setSelectedClothes] = useState<{ top: string | null, bottom: string | null }>({ top: null, bottom: null });

    const handleClothingSelect = (item: any) => {
        if (!item.supported) {
            return;
        }
        setSelectedClothes(prev => {
            const isCurrentlySelected = prev[item.type as keyof typeof prev] === item.id;
            return {
                ...prev,
                [item.type]: isCurrentlySelected ? null : item.id
            };
        });
    };

    // Avatar generation state
    const [genStatus, setGenStatus] = useState<GenStatus>('idle');
    const [genProgress, setGenProgress] = useState(0);
    const [genError, setGenError] = useState<string | null>(null);
    const [cameraResetTick, setCameraResetTick] = useState(0);
    const [cameraView, setCameraView] = useState<'front' | 'back' | 'left' | 'right' | 'face'>('front');
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollCountRef = useRef(0);
    const previousGeneratedAvatarUrlRef = useRef<string | null>(null);
    const selectedTopItem = MOCK_CLOTHES.find(item => item.id === selectedClothes.top) ?? null;

    const stopPolling = useCallback(() => {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        pollCountRef.current = 0;
    }, []);

    const handleResetCamera = useCallback(() => {
        setCameraResetTick(prev => prev + 1);
    }, []);

    const buildCurrentDraftSnapshot = useCallback((): StudioDraftSnapshot => ({
        height,
        weight,
        bodyType,
        gender,
        muscularity,
        bodyFatPercentage,
        manualMeasurements,
        autoMeasurements,
    }), [height, weight, bodyType, gender, muscularity, bodyFatPercentage, manualMeasurements, autoMeasurements]);

    const applyDraftSnapshot = useCallback((draft: StudioDraftSnapshot) => {
        setHeight(draft.height);
        setWeight(draft.weight);
        setBodyType(draft.bodyType);
        setGender(draft.gender);
        setMuscularity(draft.muscularity);
        setBodyFatPercentage(draft.bodyFatPercentage);
        setManualMeasurements(draft.manualMeasurements);
        setAutoMeasurements(draft.autoMeasurements);
    }, []);

    const syncProfileToState = useCallback((profile: StudioProfileResponse, preferredViewportMode?: ViewportMode) => {
        const resolvedBodyType = (profile.bodyType || 'regular').toLowerCase();
        const resolvedGender = (profile.gender || '').toLowerCase() === 'female' ? 'female' : 'male';
        const nextDraft: StudioDraftSnapshot = {
            height: Number(profile.height ?? 170),
            weight: Number(profile.weight ?? 70),
            bodyType: resolvedBodyType,
            gender: resolvedGender,
            muscularity: Number(profile.muscularity ?? getDefaultMuscularity(resolvedBodyType)),
            bodyFatPercentage: Number(profile.bodyFatPercentage ?? getDefaultBodyFatPercentage(resolvedGender, resolvedBodyType)),
            manualMeasurements: mapManualMeasurements(profile.manualMeasurements),
            autoMeasurements: mapAutoMeasurements(profile.autoMeasurements),
        };
        const nextGeneratedAvatar: StudioGeneratedAvatarState = {
            modelUrl: profile.generatedAvatar?.modelUrl ?? profile.lastAvatarModelUrl ?? null,
            generatedAt: profile.generatedAvatar?.generatedAt ?? null,
            inputHash: profile.generatedAvatar?.inputHash ?? null,
            isCurrent: Boolean(profile.generatedAvatar?.isCurrent),
        };

        setUserId(profile.userId || profile.id || 'default_user');
        applyDraftSnapshot(nextDraft);
        setSavedDraft(nextDraft);
        setSavedDraftHash(profile.draftStateHash ?? '');
        setCurrentDraftHash(profile.draftStateHash ?? '');
        setGeneratedAvatar(nextGeneratedAvatar);
        setSaveError(null);
        setSaveStatus('idle');
        setViewportMode(
            preferredViewportMode ??
            (nextGeneratedAvatar.modelUrl ? 'generated' : 'preview'),
        );
        setIsProfileLoaded(true);
    }, [applyDraftSnapshot]);

    const updateManualMeasurement = useCallback((key: keyof ManualMeasurementsState, value: number) => {
        setManualMeasurements(current => ({
            ...current,
            [key]: value,
        }));
    }, []);

    const handleGenderChange = useCallback((nextGender: 'male' | 'female') => {
        setGender(nextGender);
        setBodyType(resolveBodyTypeFromComposition(nextGender, muscularity, bodyFatPercentage));
    }, [bodyFatPercentage, muscularity]);

    const handleMuscularityChange = useCallback((value: number) => {
        setMuscularity(value);
        setBodyType(resolveBodyTypeFromComposition(gender, value, bodyFatPercentage));
    }, [bodyFatPercentage, gender]);

    const handleBodyFatPercentageChange = useCallback((value: number) => {
        setBodyFatPercentage(value);
        setBodyType(resolveBodyTypeFromComposition(gender, muscularity, value));
    }, [gender, muscularity]);

    const handleCompositionPresetSelect = useCallback((presetKey: CompositionPresetKey) => {
        const preset = getCompositionPresets(gender).find(item => item.key === presetKey);
        if (!preset) {
            return;
        }

        setMuscularity(preset.muscularity);
        setBodyFatPercentage(preset.bodyFatPercentage);
        setBodyType(BODY_TYPE_BY_COMPOSITION_PRESET[preset.key]);
    }, [gender]);

    const draftFingerprintSource = buildStudioDraftFingerprintSource(buildCurrentDraftSnapshot());

    useEffect(() => {
        const loadProfile = async () => {
            try {
                const profileRes = await profileClient.get('/api/v1/profiles/me');
                const profile = profileRes.data as StudioProfileResponse;
                if (profile) {
                    syncProfileToState(profile);
                }
            } catch (error: any) {
                if (error.response?.status === 404) { navigate('/setup'); }
                logger.error('Failed to load Studio profile.', undefined, error);
            }
        };
        loadProfile();
    }, [navigate, syncProfileToState]);

    useEffect(() => {
        let cancelled = false;
        createStudioDraftFingerprint(buildCurrentDraftSnapshot())
            .then(hash => {
                if (!cancelled) {
                    setCurrentDraftHash(hash);
                }
            })
            .catch(error => {
                logger.error('Failed to compute Studio draft fingerprint.', undefined, error);
            });

        return () => {
            cancelled = true;
        };
    }, [buildCurrentDraftSnapshot, draftFingerprintSource]);

    useEffect(() => {
        if (!generatedAvatar.modelUrl && viewportMode === 'generated') {
            setViewportMode('preview');
        }
    }, [generatedAvatar.modelUrl, viewportMode]);

    useEffect(() => {
        if (!isProfileLoaded || !generatedAvatar.modelUrl || !generatedAvatar.inputHash || !currentDraftHash) {
            return;
        }

        const generatedMatchesDraft = generatedAvatar.inputHash === currentDraftHash;

        if (!generatedMatchesDraft && viewportMode === 'generated') {
            setViewportMode('preview');
        }
    }, [
        currentDraftHash,
        generatedAvatar.inputHash,
        generatedAvatar.modelUrl,
        isProfileLoaded,
        viewportMode,
    ]);

    useEffect(() => {
        if (generatedAvatar.modelUrl && generatedAvatar.modelUrl !== previousGeneratedAvatarUrlRef.current) {
            handleResetCamera();
        }
        previousGeneratedAvatarUrlRef.current = generatedAvatar.modelUrl;
    }, [generatedAvatar.modelUrl, handleResetCamera]);

    // Cleanup polling on unmount
    useEffect(() => () => stopPolling(), [stopPolling]);

    const hasGeneratedAvatar = Boolean(generatedAvatar.modelUrl);
    const isGeneratedAvatarCurrent = Boolean(
        generatedAvatar.modelUrl &&
        currentDraftHash &&
        generatedAvatar.inputHash === currentDraftHash,
    );
    const isDraftDirty = Boolean(
        isProfileLoaded &&
        savedDraftHash &&
        currentDraftHash &&
        savedDraftHash !== currentDraftHash,
    );
    const isBusy = saveStatus === 'pending' || genStatus === 'pending';
    const generatedAvatarGeneratedAtLabel = generatedAvatar.generatedAt
        ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(generatedAvatar.generatedAt))
        : null;

    const handleBeforeUnload = useEffectEvent((event: BeforeUnloadEvent) => {
        if (!isDraftDirty) {
            return;
        }

        event.preventDefault();
        event.returnValue = '';
    });

    useBeforeUnload(handleBeforeUnload);
    usePrompt({
        when: ({ currentLocation, nextLocation }) =>
            isDraftDirty && currentLocation.pathname !== nextLocation.pathname,
        message: 'You have unsaved Studio edits. Leave this page anyway?',
    });

    const persistStudioProfile = async (
        draft: StudioDraftSnapshot,
        nextAutoMeasurements: AutoMeasurementsState = draft.autoMeasurements,
        nextGeneratedAvatar: { modelUrl: string; generatedAt?: string } | null = null,
    ) => {
        const response = await profileClient.put('/api/v1/profiles/me/studio', {
            height: draft.height,
            weight: draft.weight,
            bodyType: toBodyTypeEnum(draft.bodyType),
            gender: toGenderEnum(draft.gender),
            muscularity: draft.muscularity,
            bodyFatPercentage: draft.bodyFatPercentage,
            chestCircumference: toNullableMeasurement(draft.manualMeasurements.chest),
            waistCircumference: toNullableMeasurement(draft.manualMeasurements.waist),
            hipCircumference: toNullableMeasurement(draft.manualMeasurements.hip),
            shoulderWidth: toNullableMeasurement(draft.manualMeasurements.shoulder),
            calfCircumference: toNullableMeasurement(draft.manualMeasurements.calf),
            armLength: toNullableMeasurement(draft.manualMeasurements.armLength),
            torsoLength: toNullableMeasurement(draft.manualMeasurements.torsoLength),
            legLength: toNullableMeasurement(draft.manualMeasurements.legLength),
            autoChestCircumference: toNullableMeasurement(nextAutoMeasurements.chest),
            autoWaistCircumference: toNullableMeasurement(nextAutoMeasurements.waist),
            autoHipCircumference: toNullableMeasurement(nextAutoMeasurements.hip),
            autoArmLength: toNullableMeasurement(nextAutoMeasurements.armLength),
            autoLegLength: toNullableMeasurement(nextAutoMeasurements.legLength),
            generatedAvatar: nextGeneratedAvatar
                ? { modelUrl: nextGeneratedAvatar.modelUrl, generatedAt: nextGeneratedAvatar.generatedAt ?? null }
                : null,
        });

        return response.data as StudioProfileResponse;
    };

    const handleSaveDraft = async () => {
        const draftSnapshot = buildCurrentDraftSnapshot();
        setSaveStatus('pending');
        setSaveError(null);

        const savePromise = persistStudioProfile(draftSnapshot);
        toast.promise(savePromise, {
            loading: 'Saving Studio draft...',
            success: 'Studio draft saved.',
            error: 'Failed to save Studio draft.',
        });

        try {
            const profile = await savePromise;
            syncProfileToState(profile, hasGeneratedAvatar ? 'generated' : 'preview');
            setSaveStatus('success');
        } catch (error) {
            logger.error('Failed to save Studio draft.', undefined, error);
            setSaveStatus('error');
            setSaveError('Failed to save Studio draft.');
        }
    };

    const handleRevertChanges = () => {
        if (!savedDraft) {
            return;
        }

        applyDraftSnapshot(savedDraft);
        setCurrentDraftHash(savedDraftHash);
        setSaveStatus('idle');
        setSaveError(null);
        setGenError(null);
        setViewportMode(generatedAvatar.modelUrl ? 'generated' : 'preview');
        toast.success('Reverted to saved Studio draft.');
    };

    const handleGenerateAvatar = async () => {
        const draftSnapshot = buildCurrentDraftSnapshot();
        const draftHash = currentDraftHash || await createStudioDraftFingerprint(draftSnapshot);

        setGenStatus('pending');
        setGenProgress(5);
        setGenError(null);
        setSaveError(null);
        stopPolling();

        const generatePromise = new Promise<void>(async (resolve, reject) => {
            let taskId: string;
            try {
                await persistStudioProfile(draftSnapshot);
                const res = await avatarClient.post('/api/v1/avatar/generate-from-profile', {
                    user_id: userId,
                    height: draftSnapshot.height,
                    weight: draftSnapshot.weight,
                    body_type: draftSnapshot.bodyType,
                    gender: draftSnapshot.gender,
                    muscularity: draftSnapshot.muscularity,
                    body_fat_percentage: draftSnapshot.bodyFatPercentage,
                    chest: draftSnapshot.manualMeasurements.chest,
                    waist: draftSnapshot.manualMeasurements.waist,
                    hip: draftSnapshot.manualMeasurements.hip,
                    shoulder: draftSnapshot.manualMeasurements.shoulder,
                    calf: draftSnapshot.manualMeasurements.calf,
                    arm_length: draftSnapshot.manualMeasurements.armLength,
                    torso_length: draftSnapshot.manualMeasurements.torsoLength,
                    leg_length: draftSnapshot.manualMeasurements.legLength,
                });
                taskId = res.data.task_id;
            } catch {
                setGenStatus('error');
                const errMsg = 'Failed to save Studio state or queue avatar generation.';
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
                        const measuredAutoValues = mapAutoMeasurements(result?.measurements);
                        const nextAutoMeasurements = Object.values(measuredAutoValues).some(value => value > 0)
                            ? measuredAutoValues
                            : draftSnapshot.autoMeasurements;
                        const generatedAt = new Date().toISOString();
                        try {
                            const profile = await persistStudioProfile(
                                { ...draftSnapshot, autoMeasurements: nextAutoMeasurements },
                                nextAutoMeasurements,
                                { modelUrl: fullUrl, generatedAt },
                            );
                            syncProfileToState(profile, 'generated');
                            setSaveStatus('success');
                        } catch (persistError) {
                            logger.error('Failed to persist generated Studio state.', { task_id: taskId }, persistError);
                            setAutoMeasurements(nextAutoMeasurements);
                            setGeneratedAvatar({
                                modelUrl: fullUrl,
                                generatedAt,
                                inputHash: draftHash,
                                isCurrent: true,
                            });
                            setViewportMode('generated');
                            setSaveStatus('error');
                            setSaveError('Avatar generated, but saving its Studio metadata failed.');
                        }
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
                        renderMode={viewportMode}
                        generatedAvatarUrl={generatedAvatar.modelUrl}
                        gender={gender}
                        height={height}
                        weight={weight}
                        bodyType={bodyType}
                        muscularity={muscularity}
                        bodyFatPercentage={bodyFatPercentage}
                        animation={animation}
                        showGarment={selectedTopItem?.supported === true}
                        garmentUrl={selectedTopItem?.previewUrl ?? undefined}
                        garmentTint={selectedTopItem?.previewTint ?? undefined}
                        cameraResetTick={cameraResetTick}
                        cameraView={cameraView}
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

                <div className="absolute top-6 right-6 z-20 max-w-xs">
                    <div className="rounded-xl border border-white/10 bg-black/45 px-3 py-2 text-right backdrop-blur-md">
                        <div className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1">
                            <Sparkles className="w-3 h-3 text-white" />
                            <span className="text-[10px] font-mono tracking-widest uppercase text-white">
                                {viewportMode === 'generated' ? 'Saved Avatar' : 'Editing Preview'}
                            </span>
                        </div>
                        <p className="mt-2 text-sm font-medium text-white">
                            {hasGeneratedAvatar
                                ? viewportMode === 'generated'
                                    ? 'Your saved model is loaded'
                                    : 'Previewing new body changes'
                                : 'Previewing your first avatar'}
                        </p>
                        <p className="mt-1 text-[11px] leading-relaxed text-gray-400">
                            {hasGeneratedAvatar
                                ? viewportMode === 'generated'
                                    ? 'This model loads automatically when the user opens Studio.'
                                    : 'Generate when you want to update the saved avatar.'
                                : 'Generate once and Studio will load that saved model by default next time.'}
                        </p>
                    </div>
                </div>

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
                    setGender={handleGenderChange}
                    height={height}
                    setHeight={setHeight}
                    weight={weight}
                    setWeight={setWeight}
                    muscularity={muscularity}
                    setMuscularity={handleMuscularityChange}
                    bodyFatPercentage={bodyFatPercentage}
                    setBodyFatPercentage={handleBodyFatPercentageChange}
                    handleCompositionPresetSelect={handleCompositionPresetSelect}
                    animation={animation}
                    setAnimation={setAnimation}
                    genStatus={genStatus}
                    genProgress={genProgress}
                    genError={genError}
                    handleGenerateAvatar={handleGenerateAvatar}
                    saveStatus={saveStatus}
                    saveError={saveError}
                    handleSaveDraft={handleSaveDraft}
                    handleRevertChanges={handleRevertChanges}
                    isDraftDirty={isDraftDirty}
                    hasSavedDraft={savedDraft !== null}
                    hasGeneratedAvatar={hasGeneratedAvatar}
                    isGeneratedAvatarCurrent={isGeneratedAvatarCurrent}
                    generatedAvatarGeneratedAtLabel={generatedAvatarGeneratedAtLabel}
                    isBusy={isBusy}
                    selectedClothes={selectedClothes}
                    handleClothingSelect={handleClothingSelect}
                    mockClothes={MOCK_CLOTHES}
                    selectedGarmentName={selectedTopItem?.name ?? null}
                    autoMeasurements={autoMeasurements}
                    manualMeasurements={manualMeasurements}
                    setManualMeasurement={updateManualMeasurement}
                />
            )}
        </div>
    );
}
