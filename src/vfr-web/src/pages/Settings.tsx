import { User, Shield, Bell } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function Settings() {
    // In a real app we'd fetch user details from Profile API, for now we just rely on token status
    useAuthStore();

    return (
        <div className="max-w-4xl mx-auto w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl font-bold tracking-tight mb-8">Account Settings</h1>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                {/* Sidebar */}
                <div className="flex flex-col gap-2">
                    <button className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/10 text-white font-medium border border-white/5 transition-colors">
                        <User className="w-4 h-4" /> Profile
                    </button>
                    <button className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/5 text-gray-400 hover:text-white font-medium border border-transparent transition-colors">
                        <Shield className="w-4 h-4" /> Security
                    </button>
                    <button className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/5 text-gray-400 hover:text-white font-medium border border-transparent transition-colors">
                        <Bell className="w-4 h-4" /> Notifications
                    </button>
                </div>

                {/* Content Area */}
                <div className="md:col-span-3 space-y-6">
                    <div className="p-8 rounded-[2rem] bg-[#0a0a0a]/80 border border-white/[0.06] backdrop-blur-xl shadow-2xl">
                        <h2 className="text-xl font-semibold mb-6">Personal Information</h2>

                        <div className="space-y-5 relative">
                            <div className="space-y-2">
                                <label className="text-[12px] font-medium text-gray-400 uppercase tracking-widest ml-1">Email Address</label>
                                <input
                                    type="email"
                                    defaultValue={"admin@test.com"}
                                    className="w-full px-5 py-4 bg-[#111111] border border-white/[0.06] rounded-2xl text-white focus:outline-none focus:ring-1 focus:ring-primary shadow-inner"
                                    disabled
                                />
                                <p className="text-[11px] text-gray-500 mt-2 px-2">Your email address is managed via your identity provider.</p>
                            </div>
                        </div>

                        <div className="mt-8 pt-8 border-t border-white/[0.06]">
                            <h3 className="text-sm font-semibold text-red-400 uppercase tracking-widest mb-4">Danger Zone</h3>
                            <button className="px-5 py-3 rounded-xl bg-transparent border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors text-sm font-medium">
                                Delete Account & Biometric Data
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
