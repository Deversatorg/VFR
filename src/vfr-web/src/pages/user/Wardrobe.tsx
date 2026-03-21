export default function Wardrobe() {
    return (
        <div className="min-h-[calc(100vh-64px)] bg-[#050505] text-white relative overflow-hidden">
            <div
                className="absolute inset-0 opacity-15 pointer-events-none"
                style={{
                    backgroundImage:
                        'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
                    backgroundSize: '40px 40px',
                    backgroundPosition: 'center center',
                }}
            />

            <div className="relative z-10 mx-auto max-w-4xl px-6 py-20">
                <div className="rounded-[2rem] border border-white/10 bg-white/[0.03] p-10 backdrop-blur-xl shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
                    <div className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
                        Prototype Removed
                    </div>

                    <h1 className="mt-6 text-4xl font-semibold tracking-tight">Wardrobe integration is in progress</h1>
                    <p className="mt-4 max-w-2xl text-sm leading-7 text-white/70">
                        The old demo catalog and fake try-on loop were intentionally removed so this page no longer behaves
                        like a finished product surface. Real wardrobe behavior is being integrated through the Studio
                        avatar pipeline and garment preview flow.
                    </p>

                    <div className="mt-10 grid gap-4 md:grid-cols-3">
                        <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-white/40">Stable now</div>
                            <div className="mt-3 text-lg font-medium">Avatar baseline</div>
                            <p className="mt-2 text-sm text-white/60">Body generation and profile refinement are the current source of truth.</p>
                        </div>

                        <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-white/40">Current preview</div>
                            <div className="mt-3 text-lg font-medium">Studio garment primitive</div>
                            <p className="mt-2 text-sm text-white/60">Supported garment preview currently lives in Studio, not in a fake catalog page.</p>
                        </div>

                        <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-white/40">Next step</div>
                            <div className="mt-3 text-lg font-medium">Real wardrobe assets</div>
                            <p className="mt-2 text-sm text-white/60">The next integration will connect actual tops and bottoms instead of mock cards and timers.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
