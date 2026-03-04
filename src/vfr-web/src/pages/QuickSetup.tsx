import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { profileClient } from '../api/apiClients';
import { Ruler, Info, Activity } from 'lucide-react';

export default function QuickSetup() {
    const [height, setHeight] = useState(175);
    const [weight, setWeight] = useState(70);
    const [bodyType, setBodyType] = useState('Regular');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await profileClient.post('/api/v1/profiles/quick-setup', {
                height,
                weight,
                bodyType
            });
            navigate('/studio');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save profile setup. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-[#050505] text-white p-4 relative overflow-hidden font-sans">
            {/* Background Ambient Glow */}
            <div className="absolute top-1/2 left-1/2 w-[800px] h-[800px] bg-primary/10 rounded-full blur-[150px] -translate-x-1/2 -translate-y-1/2 pointer-events-none" />

            <div className="w-full max-w-xl backdrop-blur-3xl bg-[#0a0a0a]/80 p-10 sm:p-12 border border-white/[0.08] rounded-[2.5rem] shadow-[0_20px_60px_rgba(0,0,0,0.6)] relative z-10">

                <div className="flex justify-center mb-8 relative">
                    <div className="absolute inset-0 bg-primary/30 blur-2xl rounded-full" />
                    <div className="p-5 bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 text-primary rounded-3xl shadow-inner relative z-10">
                        <Ruler size={36} strokeWidth={1.5} className="text-white" />
                    </div>
                </div>

                <div className="text-center mb-10">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-4 backdrop-blur-md">
                        <Activity className="w-3.5 h-3.5 text-primary" />
                        <span className="text-[10px] font-semibold tracking-widest text-[#a1a1aa] uppercase">Step 1 of 2</span>
                    </div>
                    <h2 className="text-4xl font-semibold tracking-tight mb-3 text-white">Biometric Profile</h2>
                    <p className="text-[#a1a1aa] text-sm max-w-xs mx-auto">Let's generate your basic physical profile for the neural engine.</p>
                </div>

                {error && (
                    <div className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0 mt-1.5 box-shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                        <p className="leading-relaxed">{error}</p>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="grid grid-cols-2 gap-6">
                        <div className="space-y-2 group">
                            <label className="block text-[11px] font-medium text-gray-400 uppercase tracking-widest ml-1 transition-colors group-focus-within:text-primary">Height <span className="text-gray-600 normal-case">(cm)</span></label>
                            <input
                                type="number"
                                value={height}
                                onChange={e => setHeight(Number(e.target.value))}
                                required min="100" max="250"
                                className="w-full px-5 py-4 bg-[#111111] border border-white/[0.06] rounded-2xl focus:ring-1 focus:ring-primary focus:border-primary focus:outline-none text-2xl font-medium text-center transition-all duration-300 shadow-inner group-focus-within:bg-[#151515]"
                            />
                        </div>
                        <div className="space-y-2 group">
                            <label className="block text-[11px] font-medium text-gray-400 uppercase tracking-widest ml-1 transition-colors group-focus-within:text-primary">Weight <span className="text-gray-600 normal-case">(kg)</span></label>
                            <input
                                type="number"
                                value={weight}
                                onChange={e => setWeight(Number(e.target.value))}
                                required min="30" max="300"
                                className="w-full px-5 py-4 bg-[#111111] border border-white/[0.06] rounded-2xl focus:ring-1 focus:ring-primary focus:border-primary focus:outline-none text-2xl font-medium text-center transition-all duration-300 shadow-inner group-focus-within:bg-[#151515]"
                            />
                        </div>
                    </div>

                    <div className="space-y-3">
                        <label className="block text-[11px] font-medium text-gray-400 uppercase tracking-widest mx-1">Body Architecture</label>
                        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2.5">
                            {/* Display labels → backend BodyType enum: Slim, Athletic, Regular, Curvy, Plus */}
                            {(['Slim', 'Average', 'Athletic', 'Curvy', 'PlusSize'] as const).map((label) => {
                                const enumVal = label === 'Average' ? 'Regular' : label === 'PlusSize' ? 'Plus' : label;
                                return (
                                    <button
                                        key={label}
                                        type="button"
                                        onClick={() => setBodyType(enumVal)}
                                        className={`py-3.5 px-2 rounded-2xl text-[13px] font-medium transition-all duration-300 border ${bodyType === enumVal
                                            ? 'bg-primary/10 border-primary text-white shadow-[0_0_20px_rgba(19,91,236,0.15)]'
                                            : 'bg-[#111111] border-white/[0.04] text-gray-400 hover:bg-[#161616] hover:text-gray-300'
                                            }`}
                                    >
                                        {label === 'PlusSize' ? 'Plus Size' : label}
                                    </button>
                                );
                            })}
                        </div>

                        <div className="flex items-start gap-4 p-5 bg-primary/5 border border-primary/20 rounded-2xl mt-8 relative overflow-hidden group">
                            <div className="absolute inset-0 bg-gradient-to-r from-primary/0 via-primary/5 to-primary/0 -translate-x-[150%] animate-[shimmer_3s_infinite]" />
                            <div className="mt-0.5 relative z-10 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <Info className="text-primary lg:w-4 lg:h-4" size={16} />
                            </div>
                            <p className="text-[13px] text-gray-400 leading-relaxed translate-y-[2px] relative z-10">
                                We compile these metrics to initialize your neural avatar. Advanced localized adjustments can be calibrated inside the 3D studio.
                            </p>
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-4.5 mt-8 bg-primary hover:bg-primary-dark disabled:opacity-70 text-white font-medium text-[15px] rounded-2xl transition-all duration-300 shadow-[0_0_30px_rgba(19,91,236,0.25)] relative overflow-hidden group flex items-center justify-center min-h-[56px]"
                    >
                        <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-[150%] group-hover:translate-x-[150%] transition-transform duration-1000 ease-in-out" />
                        {loading ? (
                            <div className="flex items-center gap-3">
                                <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                                <span>Generating Avatar...</span>
                            </div>
                        ) : 'Initialize Avatar'}
                    </button>
                </form>
            </div>
        </div>
    );
}
