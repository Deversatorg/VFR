import React from 'react';

interface CameraPresetsProps {
    cameraView: 'front' | 'back' | 'left' | 'right' | 'face';
    onSelectView: (view: 'front' | 'back' | 'left' | 'right' | 'face') => void;
}

const CameraPresets: React.FC<CameraPresetsProps> = ({ cameraView, onSelectView }) => {
    const views = ['front', 'back', 'left', 'right', 'face'] as const;

    return (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 flex items-center p-1 border border-white/10 bg-black/50 backdrop-blur-xl rounded-2xl shadow-2xl">
            {views.map(v => (
                <button
                    key={v}
                    onClick={() => onSelectView(v)}
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
    );
};

export default CameraPresets;
