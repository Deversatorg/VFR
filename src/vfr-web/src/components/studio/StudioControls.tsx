import React from 'react';
import { Cpu, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';

interface ClothingItem {
    id: string;
    type: string;
    name: string;
    color: string;
}

interface StudioControlsProps {
    activeTab: 'body' | 'wardrobe';
    setActiveTab: (tab: 'body' | 'wardrobe') => void;
    gender: 'male' | 'female';
    setGender: (gender: 'male' | 'female') => void;
    localHeight: number;
    setLocalHeight: (height: number) => void;
    localWeight: number;
    setLocalWeight: (weight: number) => void;
    bodyType: string;
    setBodyType: (type: string) => void;
    animation: string;
    setAnimation: (anim: any) => void;
    genStatus: 'idle' | 'pending' | 'success' | 'error';
    genProgress: number;
    genError: string | null;
    handleGenerateAvatar: () => void;
    selectedClothes: { top: string | null; bottom: string | null };
    handleClothingSelect: (item: ClothingItem) => void;
    mockClothes: ClothingItem[];
    chest: number;
    setChest: (v: number) => void;
    waist: number;
    setWaist: (v: number) => void;
    hip: number;
    setHip: (v: number) => void;
    shoulder: number;
    setShoulder: (v: number) => void;
    calf: number;
    setCalf: (v: number) => void;
    armLength: number;
    setArmLength: (v: number) => void;
    torsoLength: number;
    setTorsoLength: (v: number) => void;
    legLength: number;
    setLegLength: (v: number) => void;
}

const StudioControls: React.FC<StudioControlsProps> = ({
    activeTab,
    setActiveTab,
    gender,
    setGender,
    localHeight,
    setLocalHeight,
    localWeight,
    setLocalWeight,
    bodyType,
    setBodyType,
    animation,
    setAnimation,
    genStatus,
    genProgress,
    genError,
    handleGenerateAvatar,
    selectedClothes,
    handleClothingSelect,
    mockClothes,
    chest,
    setChest,
    waist,
    setWaist,
    hip,
    setHip,
    shoulder,
    setShoulder,
    calf,
    setCalf,
    armLength,
    setArmLength,
    torsoLength,
    setTorsoLength,
    legLength,
    setLegLength,
}) => {
    return (
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
                    
                    {/* Measurements Section */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Measurements</span>
                            <span className="text-[9px] font-medium text-gray-600 uppercase tracking-widest border border-white/10 rounded-md px-1.5 py-0.5">Optional</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {([
                                { label: 'Chest', value: chest, set: setChest },
                                { label: 'Waist', value: waist, set: setWaist },
                                { label: 'Hip', value: hip, set: setHip },
                                { label: 'Shoulder', value: shoulder, set: setShoulder },
                                { label: 'Calf', value: calf, set: setCalf },
                                { label: 'Arm Length', value: armLength, set: setArmLength },
                                { label: 'Torso Length', value: torsoLength, set: setTorsoLength },
                                { label: 'Leg Length', value: legLength, set: setLegLength },
                            ] as const).map(({ label, value, set }) => (
                                <div key={label} className="space-y-1">
                                    <span className="text-[10px] text-gray-500 ml-0.5">{label} <span className="text-gray-600">(cm)</span></span>
                                    <input
                                        type="number"
                                        min="0"
                                        max="300"
                                        placeholder="0 = auto"
                                        value={value === 0 ? '' : value}
                                        onChange={e => set(e.target.value === '' ? 0 : Number(e.target.value))}
                                        className="w-full px-3 py-2 bg-[#111111] border border-white/5 rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
                                    />
                                </div>
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
                        <span className="text-xs text-gray-500">{mockClothes.length} Items</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 pb-8">
                        {mockClothes.map(item => {
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
    );
};

export default StudioControls;
