import React, { useMemo } from 'react';
import { AlertCircle, CheckCircle2, ChevronDown, Cpu, RotateCcw, Save, Sparkles } from 'lucide-react';
import type { AutoMeasurementsState, ManualMeasurementsState } from './studioState';

interface ClothingItem {
    id: string;
    type: 'top' | 'bottom';
    name: string;
    color: string;
    supported?: boolean;
    previewNote?: string | null;
}

type SaveStatus = 'idle' | 'pending' | 'success' | 'error';
type CompositionPresetKey = 'lean' | 'athletic' | 'average' | 'soft';

interface StudioControlsProps {
    activeTab: 'body' | 'wardrobe';
    setActiveTab: (tab: 'body' | 'wardrobe') => void;
    gender: 'male' | 'female';
    setGender: (gender: 'male' | 'female') => void;
    height: number;
    setHeight: (height: number) => void;
    weight: number;
    setWeight: (weight: number) => void;
    muscularity: number;
    setMuscularity: (value: number) => void;
    bodyFatPercentage: number;
    setBodyFatPercentage: (value: number) => void;
    handleCompositionPresetSelect: (presetKey: CompositionPresetKey) => void;
    animation: string;
    setAnimation: (anim: 'idle' | 'walk' | 'run' | 'jump' | 'tpose') => void;
    genStatus: 'idle' | 'pending' | 'success' | 'error';
    genProgress: number;
    genError: string | null;
    genPhaseLabel: string | null;
    handleGenerateAvatar: () => void;
    saveStatus: SaveStatus;
    saveError: string | null;
    handleSaveDraft: () => void;
    handleRevertChanges: () => void;
    isDraftDirty: boolean;
    hasSavedDraft: boolean;
    hasGeneratedAvatar: boolean;
    isGeneratedAvatarCurrent: boolean;
    generatedAvatarGeneratedAtLabel: string | null;
    isBusy: boolean;
    selectedClothes: { top: string | null; bottom: string | null };
    handleClothingSelect: (item: ClothingItem) => void;
    mockClothes: readonly ClothingItem[];
    selectedGarmentName: string | null;
    autoMeasurements: AutoMeasurementsState;
    manualMeasurements: ManualMeasurementsState;
    setManualMeasurement: (key: MeasurementFieldKey, value: number) => void;
}

type MeasurementFieldKey =
    | 'chest'
    | 'waist'
    | 'hip'
    | 'shoulder'
    | 'calf'
    | 'armLength'
    | 'torsoLength'
    | 'legLength';

type CompositionPreset = {
    key: CompositionPresetKey;
    label: string;
    muscularity: number;
    bodyFatPercentage: number;
    note: string;
};

const formatMeasurement = (value: number) => value.toFixed(1);

function getCompositionPresets(gender: 'male' | 'female'): CompositionPreset[] {
    return gender === 'female'
        ? [
            { key: 'lean', label: 'Lean', muscularity: 32, bodyFatPercentage: 18, note: 'Sharper and lighter silhouette.' },
            { key: 'athletic', label: 'Athletic', muscularity: 58, bodyFatPercentage: 22, note: 'Sportier with more definition.' },
            { key: 'average', label: 'Average', muscularity: 44, bodyFatPercentage: 28, note: 'Balanced everyday proportions.' },
            { key: 'soft', label: 'Soft', muscularity: 30, bodyFatPercentage: 34, note: 'Softer distribution and less definition.' },
        ]
        : [
            { key: 'lean', label: 'Lean', muscularity: 42, bodyFatPercentage: 11, note: 'Drier frame with less softness.' },
            { key: 'athletic', label: 'Athletic', muscularity: 72, bodyFatPercentage: 14, note: 'More muscle volume and definition.' },
            { key: 'average', label: 'Average', muscularity: 52, bodyFatPercentage: 19, note: 'Balanced baseline body shape.' },
            { key: 'soft', label: 'Soft', muscularity: 36, bodyFatPercentage: 26, note: 'Softer shape with less sharpness.' },
        ];
}

const StudioControls: React.FC<StudioControlsProps> = ({
    activeTab,
    setActiveTab,
    gender,
    setGender,
    height,
    setHeight,
    weight,
    setWeight,
    muscularity,
    setMuscularity,
    bodyFatPercentage,
    setBodyFatPercentage,
    handleCompositionPresetSelect,
    animation,
    setAnimation,
    genStatus,
    genProgress,
    genError,
    genPhaseLabel,
    handleGenerateAvatar,
    saveStatus,
    saveError,
    handleSaveDraft,
    handleRevertChanges,
    isDraftDirty,
    hasSavedDraft,
    hasGeneratedAvatar,
    isGeneratedAvatarCurrent,
    generatedAvatarGeneratedAtLabel,
    isBusy,
    selectedClothes,
    handleClothingSelect,
    mockClothes,
    selectedGarmentName,
    autoMeasurements,
    manualMeasurements,
    setManualMeasurement,
}) => {
    const compositionPresets = useMemo(() => getCompositionPresets(gender), [gender]);
    const activePreset = useMemo(
        () => compositionPresets.find((preset) =>
            Math.round(muscularity) === preset.muscularity &&
            Math.round(bodyFatPercentage) === preset.bodyFatPercentage,
        )?.key ?? 'custom',
        [bodyFatPercentage, compositionPresets, muscularity],
    );

    const measurementFields = useMemo(() => ([
        { key: 'chest' as const, label: 'Chest', manualValue: manualMeasurements.chest, autoValue: autoMeasurements.chest },
        { key: 'waist' as const, label: 'Waist', manualValue: manualMeasurements.waist, autoValue: autoMeasurements.waist },
        { key: 'hip' as const, label: 'Hips', manualValue: manualMeasurements.hip, autoValue: autoMeasurements.hip },
        { key: 'shoulder' as const, label: 'Shoulders', manualValue: manualMeasurements.shoulder, autoValue: 0 },
        { key: 'calf' as const, label: 'Calf', manualValue: manualMeasurements.calf, autoValue: 0 },
        { key: 'armLength' as const, label: 'Arm Length', manualValue: manualMeasurements.armLength, autoValue: autoMeasurements.armLength },
        { key: 'torsoLength' as const, label: 'Torso Length', manualValue: manualMeasurements.torsoLength, autoValue: 0 },
        { key: 'legLength' as const, label: 'Leg Length', manualValue: manualMeasurements.legLength, autoValue: autoMeasurements.legLength },
    ]), [autoMeasurements, manualMeasurements]);

    const customMeasurementCount = measurementFields.filter((field) => field.manualValue > 0).length;

    return (
        <div className="w-full md:w-1/3 h-[40vh] md:h-full bg-[#0a0a0a] shadow-[0_-20px_40px_rgba(0,0,0,0.5)] md:shadow-none z-20 overflow-y-auto p-4 md:p-6 md:rounded-none flex flex-col gap-6 scrollbar-hide pb-24 md:pb-6 relative rounded-t-2xl">
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

            {activeTab === 'body' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="rounded-2xl border border-white/5 bg-[#111111] p-4">
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <span className="text-[11px] font-medium uppercase tracking-wider text-gray-400">Saved Model</span>
                                <p className="mt-2 text-sm font-semibold text-white">
                                    {hasGeneratedAvatar
                                        ? 'Your avatar loads automatically when Studio opens.'
                                        : 'Generate once to save your avatar for the next visit.'}
                                </p>
                                <p className="mt-1 text-xs leading-relaxed text-gray-500">
                                    Save keeps your body settings. Generate refreshes the actual avatar model for this user.
                                </p>
                            </div>
                            <span className={`rounded-full px-2 py-1 text-[9px] font-medium uppercase tracking-wider ${isDraftDirty ? 'bg-amber-500/10 text-amber-300' : 'bg-emerald-500/10 text-emerald-300'}`}>
                                {isDraftDirty ? 'Unsaved edits' : 'In sync'}
                            </span>
                        </div>

                        {generatedAvatarGeneratedAtLabel && (
                            <p className="mt-3 text-xs text-gray-400">
                                Last generated: <span className="text-white">{generatedAvatarGeneratedAtLabel}</span>
                            </p>
                        )}

                        {hasGeneratedAvatar && !isGeneratedAvatarCurrent && (
                            <p className="mt-2 text-xs leading-relaxed text-amber-300">
                                You changed body settings after the last generation. Generate again when you want to refresh the saved avatar.
                            </p>
                        )}

                        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                            <button
                                type="button"
                                onClick={handleSaveDraft}
                                disabled={isBusy || !isDraftDirty}
                                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm font-medium text-white transition-all hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <Save className="h-4 w-4" />
                                <span>{saveStatus === 'pending' ? 'Saving...' : 'Save Changes'}</span>
                            </button>
                            <button
                                type="button"
                                onClick={handleRevertChanges}
                                disabled={isBusy || !hasSavedDraft || !isDraftDirty}
                                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/10 bg-transparent px-3 py-3 text-sm font-medium text-gray-300 transition-all hover:border-white/20 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <RotateCcw className="h-4 w-4" />
                                <span>Revert</span>
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Base Frame</span>
                        <div className="flex gap-2">
                            {(['male', 'female'] as const).map((type) => (
                                <button
                                    key={type}
                                    onClick={() => setGender(type)}
                                    disabled={isBusy}
                                    className={`flex-1 py-2 rounded-xl text-xs font-medium transition-all ${gender === type ? 'bg-primary/20 text-primary border border-primary/50' : 'bg-[#111111] text-gray-400 border border-white/5 hover:bg-white/5'} disabled:cursor-not-allowed disabled:opacity-50`}
                                >
                                    {type.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between items-end">
                            <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Height</span>
                            <span className="text-sm text-white font-mono">{height} cm</span>
                        </div>
                        <input
                            type="range"
                            min="140"
                            max="220"
                            value={height}
                            onChange={(event) => setHeight(Number(event.target.value))}
                            disabled={isBusy}
                            className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-50"
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between items-end">
                            <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Weight</span>
                            <span className="text-sm text-white font-mono">{weight} kg</span>
                        </div>
                        <input
                            type="range"
                            min="40"
                            max="150"
                            value={weight}
                            onChange={(event) => setWeight(Number(event.target.value))}
                            disabled={isBusy}
                            className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                        />
                    </div>

                    <div className="space-y-4 rounded-2xl border border-white/5 bg-[#111111] p-4">
                        <div className="flex items-center justify-between">
                            <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Body Composition</span>
                            <span className="text-[9px] font-medium text-gray-600 uppercase tracking-widest border border-white/10 rounded-md px-1.5 py-0.5">Primary control</span>
                        </div>

                        <p className="text-[11px] text-gray-500 leading-relaxed">
                            Pick a preset or fine-tune the sliders. If you move a slider away from a preset, Studio switches to <span className="text-gray-300">Custom</span>.
                        </p>

                        <div className="grid grid-cols-2 gap-2">
                            {compositionPresets.map((preset) => (
                                <button
                                    key={preset.key}
                                    type="button"
                                    onClick={() => handleCompositionPresetSelect(preset.key)}
                                    disabled={isBusy}
                                    className={`rounded-xl border px-3 py-2 text-left transition-all ${activePreset === preset.key ? 'border-primary/50 bg-primary/15 text-white' : 'border-white/5 bg-[#0d0d0d] text-gray-300 hover:border-white/15'} disabled:cursor-not-allowed disabled:opacity-50`}
                                >
                                    <div className="text-xs font-semibold">{preset.label}</div>
                                    <div className="mt-1 text-[10px] text-gray-500 leading-relaxed">{preset.note}</div>
                                </button>
                            ))}
                            <div className={`rounded-xl border px-3 py-2 ${activePreset === 'custom' ? 'border-amber-400/40 bg-amber-500/10' : 'border-white/5 bg-[#0d0d0d]'}`}>
                                <div className={`text-xs font-semibold ${activePreset === 'custom' ? 'text-amber-200' : 'text-gray-400'}`}>Custom</div>
                                <div className="mt-1 text-[10px] text-gray-500 leading-relaxed">Active when the sliders do not match a preset.</div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-end">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Muscularity</span>
                                <span className="text-sm text-white font-mono">{Math.round(muscularity)}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={muscularity}
                                onChange={(event) => setMuscularity(Number(event.target.value))}
                                disabled={isBusy}
                                className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-end">
                                <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Body Fat</span>
                                <span className="text-sm text-white font-mono">{Math.round(bodyFatPercentage)}%</span>
                            </div>
                            <input
                                type="range"
                                min="2"
                                max="55"
                                value={bodyFatPercentage}
                                onChange={(event) => setBodyFatPercentage(Number(event.target.value))}
                                disabled={isBusy}
                                className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
                            />
                        </div>
                    </div>

                    <details className="rounded-2xl border border-white/5 bg-[#111111] p-4 group">
                        <summary className="flex cursor-pointer list-none items-start justify-between gap-3 [&::-webkit-details-marker]:hidden">
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Advanced Fit</span>
                                    <span className="text-[9px] font-medium text-gray-600 uppercase tracking-widest border border-white/10 rounded-md px-1.5 py-0.5">Optional</span>
                                </div>
                                <p className="mt-2 text-[11px] text-gray-500 leading-relaxed">
                                    Open this if you want to refine waist, shoulders, torso and other body regions manually.
                                </p>
                                <p className="mt-2 text-xs text-gray-400">
                                    {customMeasurementCount > 0 ? `${customMeasurementCount} manual refinements active` : 'Using automatic measurements'}
                                </p>
                            </div>
                            <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-gray-500 transition-transform group-open:rotate-180" />
                        </summary>

                        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
                            {measurementFields.map((field) => (
                                <div key={field.key} className="rounded-2xl border border-white/5 bg-[#0d0d0d] p-3">
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] text-gray-400 uppercase tracking-wider">{field.label}</span>
                                                <span className={`rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider ${field.manualValue > 0 ? 'bg-amber-500/10 text-amber-300' : 'bg-white/8 text-gray-300'}`}>
                                                    {field.manualValue > 0 ? 'Custom' : 'Auto'}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-[11px] text-gray-500">
                                                {field.autoValue > 0 ? `Auto baseline ${formatMeasurement(field.autoValue)} cm` : 'No auto baseline yet'}
                                            </p>
                                        </div>
                                        {field.manualValue > 0 && (
                                            <button
                                                type="button"
                                                onClick={() => setManualMeasurement(field.key, 0)}
                                                disabled={isBusy}
                                                className="inline-flex items-center gap-1 rounded-lg border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] font-medium text-primary transition-all hover:bg-primary/15 disabled:cursor-not-allowed disabled:opacity-50"
                                            >
                                                <RotateCcw className="h-3 w-3" />
                                                Reset
                                            </button>
                                        )}
                                    </div>
                                    <div className="mt-3 flex items-center gap-2 rounded-xl border border-white/5 bg-[#111111] px-3 py-2">
                                        <input
                                            type="number"
                                            min="0"
                                            max="300"
                                            placeholder={field.autoValue > 0 ? `${formatMeasurement(field.autoValue)}` : 'Enter cm'}
                                            value={field.manualValue === 0 ? '' : field.manualValue}
                                            onChange={(event) => setManualMeasurement(field.key, event.target.value === '' ? 0 : Number(event.target.value))}
                                            disabled={isBusy}
                                            className="w-full bg-transparent text-xs text-white placeholder-gray-600 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                                        />
                                        <span className="text-[10px] uppercase tracking-widest text-gray-600">cm</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </details>

                    <div className="space-y-2">
                        <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Animation State</span>
                        <div className="grid grid-cols-3 gap-2">
                            {(['idle', 'walk', 'run', 'jump', 'tpose'] as const).map((anim) => (
                                <button
                                    key={anim}
                                    onClick={() => setAnimation(anim)}
                                    disabled={isBusy}
                                    className={`py-2 rounded-xl text-[10px] items-center justify-center flex font-medium transition-all ${animation === anim ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50' : 'bg-[#111111] text-gray-400 border border-white/5 hover:bg-white/5'} disabled:cursor-not-allowed disabled:opacity-50`}
                                >
                                    {anim.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleGenerateAvatar}
                        disabled={isBusy}
                        className="w-full mt-2 py-3.5 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/80 hover:to-blue-600/80 disabled:opacity-50 rounded-xl text-white font-semibold shadow-lg transition-all flex items-center justify-center gap-2 disabled:cursor-not-allowed"
                    >
                        {genStatus === 'pending' ? (
                            <>
                                <Cpu className="w-5 h-5 animate-spin" />
                                <span>{genPhaseLabel ?? 'Generating your avatar'}... {Math.max(5, genProgress)}%</span>
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-5 h-5" />
                                <span>Generate My Avatar</span>
                            </>
                        )}
                    </button>

                    {saveStatus === 'success' && !isDraftDirty && (
                        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3">
                            <p className="text-xs text-emerald-300 leading-relaxed">Body settings saved.</p>
                        </div>
                    )}

                    {saveError && (
                        <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                            <p className="text-xs text-red-400 leading-relaxed">{saveError}</p>
                        </div>
                    )}

                    {genStatus === 'error' && genError && (
                        <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                            <p className="text-xs text-red-400 leading-relaxed">{genError}</p>
                        </div>
                    )}
                </div>
            )}

            {activeTab === 'wardrobe' && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="rounded-2xl border border-white/5 bg-[#111111] p-4">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <span className="text-sm font-semibold text-white">Apparel Library</span>
                                <p className="mt-1 text-xs text-gray-500">
                                    Supported tops preview directly on the body currently shown in Studio. This keeps wardrobe fast while we build out the full production garment pipeline.
                                </p>
                            </div>
                            <span className="text-xs text-gray-500">{mockClothes.length} Items</span>
                        </div>

                        <div className="mt-4 rounded-xl border border-white/5 bg-[#0c0c0c] px-3 py-2">
                            <p className="text-[10px] uppercase tracking-widest text-gray-500">Current garment preview</p>
                            <p className="mt-1 text-sm font-medium text-white">{selectedGarmentName ? selectedGarmentName : 'No garment selected'}</p>
                            <p className="mt-1 text-xs text-gray-500">
                                {selectedGarmentName ? 'Rendered on your current Studio body view.' : 'Pick a supported top card to preview it in the viewport.'}
                            </p>
                            {!isGeneratedAvatarCurrent && hasGeneratedAvatar && (
                                <p className="mt-2 text-[11px] text-amber-300">
                                    You changed body settings after the last generation, so garment fit is approximate until you regenerate the avatar.
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pb-8">
                        {mockClothes.map((item) => {
                            const isSelected = selectedClothes.top === item.id || selectedClothes.bottom === item.id;
                            const isSupported = item.supported !== false;

                            return (
                                <button
                                    type="button"
                                    key={item.id}
                                    onClick={() => handleClothingSelect(item)}
                                    disabled={isBusy || !isSupported}
                                    className={`relative overflow-hidden rounded-2xl border-2 text-left transition-all duration-200 ${isSelected ? 'border-primary shadow-[0_0_15px_rgba(19,91,236,0.3)]' : 'border-[#1a1a1a] hover:border-white/20'} ${isSupported ? 'cursor-pointer' : 'cursor-not-allowed opacity-65'} ${isBusy ? 'opacity-60' : ''}`}
                                >
                                    <div className="flex aspect-[4/5] flex-col bg-[#111111] p-3">
                                        <div className="mb-3 flex-1 rounded-xl shadow-inner opacity-80" style={{ backgroundColor: item.color }} />
                                        <div className="flex items-start justify-between gap-2">
                                            <div>
                                                <p className="text-xs font-medium text-white line-clamp-1">{item.name}</p>
                                                <p className="text-[10px] text-gray-500 capitalize mt-0.5">{item.type}</p>
                                                {item.previewNote && (
                                                    <p className="mt-1 text-[10px] text-gray-500 leading-relaxed">{item.previewNote}</p>
                                                )}
                                            </div>
                                            {isSelected ? (
                                                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                                            ) : (
                                                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider ${isSupported ? 'bg-primary/10 text-primary' : 'bg-white/5 text-gray-500'}`}>
                                                    {isSupported ? 'Preview' : 'Next'}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default StudioControls;
