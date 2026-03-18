import { useState } from 'react';
import { Camera, RefreshCcw, Sparkles, Shirt, Scissors } from 'lucide-react';

// Mock data for catalog
const CATALOG_ITEMS = [
    {
        id: 'c1',
        title: 'Classic White Tee',
        category: 'T-Shirts',
        price: '$25',
        imageUrl: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
    },
    {
        id: 'c2',
        title: 'Denim Jacket',
        category: 'Outerwear',
        price: '$89',
        imageUrl: 'https://images.unsplash.com/photo-1576871337622-98d48d1cf531?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
    },
    {
        id: 'c3',
        title: 'Cyberpunk Hoodie',
        category: 'Hoodies',
        price: '$65',
        imageUrl: 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
    },
    {
        id: 'c4',
        title: 'Silk Evening Dress',
        category: 'Dresses',
        price: '$120',
        imageUrl: 'https://images.unsplash.com/photo-1539008835657-9e8e9680c956?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
    }
];

export default function Wardrobe() {
    const [selectedItem, setSelectedItem] = useState<typeof CATALOG_ITEMS[0] | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [resultImage, setResultImage] = useState<string | null>(null);

    const handleTryOn = () => {
        if (!selectedItem) return;
        setIsGenerating(true);
        // Mock API call to VTON Service
        setTimeout(() => {
            setIsGenerating(false);
            setResultImage(selectedItem.imageUrl); // For now, just show the item itself as a mock result
        }, 4000);
    };

    return (
        <div className="flex h-[calc(100vh-64px)] overflow-hidden">
            {/* Left Panel - Control Center */}
            <div className="w-80 bg-[#0f0f0f] border-r border-[#222] flex flex-col relative z-20">
                <div className="p-6">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-white to-gray-500 bg-clip-text text-transparent flex items-center gap-2">
                        <Shirt className="w-5 h-5 text-primary" />
                        Wardrobe
                    </h2>
                    <p className="text-xs text-gray-500 mt-1">Select an item to try on</p>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                    {CATALOG_ITEMS.map((item) => (
                        <div
                            key={item.id}
                            onClick={() => setSelectedItem(item)}
                            className={`group cursor-pointer rounded-xl overflow-hidden border transition-all ${selectedItem?.id === item.id
                                    ? 'border-primary bg-primary/10'
                                    : 'border-white/10 bg-white/5 hover:border-white/30'
                                }`}
                        >
                            <div className="aspect-[3/4] overflow-hidden relative">
                                <img
                                    src={item.imageUrl}
                                    alt={item.title}
                                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                                />
                                {selectedItem?.id === item.id && (
                                    <div className="absolute top-2 right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                                        <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                                    </div>
                                )}
                            </div>
                            <div className="p-3">
                                <h3 className="text-sm font-medium text-white">{item.title}</h3>
                                <div className="flex justify-between items-center mt-1">
                                    <span className="text-xs text-gray-400">{item.category}</span>
                                    <span className="text-sm font-mono text-primary">{item.price}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="p-4 border-t border-[#222] bg-[#0f0f0f]">
                    <button
                        onClick={handleTryOn}
                        disabled={!selectedItem || isGenerating}
                        className={`w-full py-3 px-4 rounded-xl font-medium tracking-wide flex items-center justify-center gap-2 transition-all ${!selectedItem
                                ? 'bg-white/5 text-gray-500 cursor-not-allowed'
                                : isGenerating
                                    ? 'bg-primary/50 text-white cursor-wait'
                                    : 'bg-primary hover:bg-primary/90 text-black hover:shadow-[0_0_20px_rgba(230,255,0,0.3)] shadow-[0_0_10px_rgba(230,255,0,0.1)]'
                            }`}
                    >
                        {isGenerating ? (
                            <>
                                <RefreshCcw className="w-4 h-4 animate-spin" />
                                Processing AI...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-4 h-4" />
                                Virtual Try-On
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Right Panel - Result Area */}
            <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden">
                {/* Neural grid background */}
                <div className="absolute inset-0 opacity-20 pointer-events-none" style={{
                    backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
                    backgroundSize: '40px 40px',
                    backgroundPosition: 'center center'
                }} />

                {isGenerating ? (
                    <div className="text-center relative z-10 flex flex-col items-center">
                        <div className="w-24 h-24 relative mb-6">
                            <div className="absolute inset-0 border-t-2 border-primary rounded-full animate-spin" />
                            <div className="absolute inset-2 border-r-2 border-white/20 rounded-full animate-[spin_1.5s_linear_infinite]" />
                            <div className="absolute inset-4 border-b-2 border-blue-500/50 rounded-full animate-[spin_2s_linear_infinite]" />
                            <Scissors className="w-6 h-6 text-primary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                        </div>
                        <h3 className="text-2xl font-light text-white tracking-widest uppercase mb-2">Stitching Fabrics</h3>
                        <p className="text-primary font-mono text-sm max-w-sm">Applying neural diffusion to simulate cloth draping...</p>
                    </div>
                ) : resultImage ? (
                    <div className="relative z-10 w-full max-w-lg p-8">
                        <div className="aspect-[3/4] rounded-2xl overflow-hidden ring-1 ring-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
                            <img
                                src={resultImage}
                                alt="Try-On Result"
                                className="w-full h-full object-cover"
                            />
                        </div>
                        <div className="mt-8 flex justify-center gap-4">
                            <button className="flex items-center gap-2 px-6 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-lg border border-white/10 transition-colors">
                                <Camera className="w-4 h-4" />
                                Download Lookbook
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="text-center relative z-10">
                        <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6 ring-1 ring-white/10">
                            <Shirt className="w-8 h-8 text-white/30" />
                        </div>
                        <h3 className="text-2xl font-light text-white/50 tracking-widest uppercase mb-2">Awaiting Selection</h3>
                        <p className="text-white/20 font-mono text-sm max-w-sm mx-auto">Select a garment from the catalog to initiate neural try-on synthesis.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
