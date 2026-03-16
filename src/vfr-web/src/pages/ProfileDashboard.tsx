import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, CreditCard, LogOut, CheckCircle2, Shield, KeyRound, ChevronRight, Bell } from 'lucide-react';
import Billing from './Billing';
import { useAuthStore } from '../store/authStore';

export default function ProfileDashboard() {
    const [activeTab, setActiveTab] = useState<'account' | 'billing' | 'security' | 'notifications'>('account');
    const { role, email, logout } = useAuthStore();
    const navigate = useNavigate();

    const handleSignOut = () => {
        logout();
        navigate('/login', { replace: true });
    };

    const userEmail = email || "user@example.com";
    const userRole = role || "Standard User";
    const userInitials = userEmail.substring(0, 2).toUpperCase();

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col md:flex-row gap-8">
                
                {/* Sidebar Navigation */}
                <div className="w-full md:w-64 shrink-0 flex flex-col gap-2">
                    <div className="hidden md:block mb-6 px-4">
                        <h2 className="text-xl font-semibold text-white tracking-tight">Personal Cabinet</h2>
                        <p className="text-sm text-gray-500 mt-1">Manage your experience.</p>
                    </div>

                    {/* Mobile: Horizontal scrollable tabs; Desktop: Stacked buttons */}
                    <div className="flex md:flex-col overflow-x-auto md:overflow-visible gap-2 pb-2 md:pb-0 scrollbar-hide">
                        <button
                            onClick={() => setActiveTab('account')}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                                activeTab === 'account' 
                                ? 'bg-primary/10 text-primary md:border md:border-primary/20 shadow-sm' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            <User className="w-5 h-5 shrink-0" />
                            Account Details
                        </button>
                        
                        <button
                            onClick={() => setActiveTab('security')}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                                activeTab === 'security' 
                                ? 'bg-primary/10 text-primary md:border md:border-primary/20 shadow-sm' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            <Shield className="w-5 h-5 shrink-0" />
                            Security
                        </button>

                        <button
                            onClick={() => setActiveTab('notifications')}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                                activeTab === 'notifications' 
                                ? 'bg-primary/10 text-primary md:border md:border-primary/20 shadow-sm' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            <Bell className="w-5 h-5 shrink-0" />
                            Notifications
                        </button>

                        <button
                            onClick={() => setActiveTab('billing')}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                                activeTab === 'billing' 
                                ? 'bg-primary/10 text-primary md:border md:border-primary/20 shadow-sm' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            <CreditCard className="w-5 h-5 shrink-0" />
                            Billing & Plans
                        </button>

                        <div className="hidden md:block my-4 border-t border-white/5"></div>

                        <button
                            onClick={handleSignOut}
                            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all whitespace-nowrap"
                        >
                            <LogOut className="w-5 h-5 shrink-0" />
                            Sign Out
                        </button>
                    </div>
                </div>

                {/* Main Content Area */}
                <div className="flex-1 bg-[#0a0a0a] border border-white/5 rounded-[2rem] p-6 sm:p-10 shadow-2xl relative overflow-hidden min-h-[500px]">
                    {/* Subtle Top Gradient */}
                    <div className="absolute top-0 inset-x-0 h-32 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />

                    {activeTab === 'account' && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-500 relative z-10 space-y-8">
                            <div>
                                <h1 className="text-2xl font-semibold text-white tracking-tight mb-2">Account Details</h1>
                                <p className="text-gray-400 text-sm">Review your profile identity and security settings.</p>
                            </div>

                            {/* User Identity Card */}
                            <div className="bg-[#111111] border border-white/5 rounded-2xl p-6 sm:p-8 flex items-center justify-between shadow-xl">
                                <div className="flex items-center gap-5 sm:gap-6">
                                    <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-xl sm:text-2xl font-bold text-white shadow-lg shadow-primary/20">
                                        {userInitials}
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-lg sm:text-xl font-semibold text-white tracking-tight">{userEmail}</h3>
                                            <Shield className="w-4 h-4 text-emerald-500 hidden sm:block" />
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="px-2.5 py-0.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-gray-400 tracking-wide capitalize">
                                                {userRole}
                                            </span>
                                            <span className="text-emerald-500 text-xs font-medium flex items-center gap-1">
                                                <CheckCircle2 className="w-3 h-3" /> Verified
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Personal Information (Settings Merge) */}
                            <div className="bg-[#111111] border border-white/5 rounded-2xl p-6 sm:p-8 shadow-xl">
                                <h3 className="text-base font-semibold text-white mb-6">Personal Information</h3>
                                <div className="space-y-2">
                                    <label className="text-[12px] font-medium text-gray-400 uppercase tracking-widest ml-1">Email Address</label>
                                    <input
                                        type="email"
                                        defaultValue={userEmail}
                                        className="w-full px-5 py-4 bg-[#0a0a0a] border border-white/[0.06] rounded-2xl text-white focus:outline-none focus:ring-1 focus:ring-primary shadow-inner opacity-80 cursor-not-allowed"
                                        disabled
                                    />
                                    <p className="text-[11px] text-gray-500 mt-2 px-2">Your email address is managed via your identity provider.</p>
                                </div>

                                <div className="mt-8 pt-8 border-t border-white/[0.06]">
                                    <h3 className="text-sm font-semibold text-red-400 uppercase tracking-widest mb-4">Danger Zone</h3>
                                    <button className="px-5 py-3 rounded-xl bg-transparent border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors text-sm font-medium">
                                        Delete Account & Biometric Data
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'security' && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-500 relative z-10 space-y-8">
                             <div>
                                <h1 className="text-2xl font-semibold text-white tracking-tight mb-2">Security</h1>
                                <p className="text-gray-400 text-sm">Manage your account authentication and password.</p>
                            </div>
                            
                            {/* Security Settings Module */}
                            <div className="bg-[#111111] border border-white/5 rounded-2xl p-6 sm:p-8 shadow-xl">
                                <h3 className="text-base font-semibold text-white mb-6">Authentication</h3>
                                
                                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-4 border-b border-white/5">
                                    <div className="flex items-start gap-4">
                                        <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center shrink-0">
                                            <KeyRound className="w-5 h-5 text-gray-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-medium text-white mb-0.5">Account Password</h4>
                                            <p className="text-xs text-gray-500">Reset your password to keep your account secure.</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => navigate('/forgot-password')}
                                        className="shrink-0 flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-medium text-gray-300 transition-all w-full sm:w-auto justify-center"
                                    >
                                        Reset Password
                                        <ChevronRight className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'notifications' && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-500 relative z-10 space-y-8">
                             <div>
                                <h1 className="text-2xl font-semibold text-white tracking-tight mb-2">Notifications</h1>
                                <p className="text-gray-400 text-sm">Manage email and application alerts.</p>
                            </div>
                            
                            <div className="bg-[#111111] border border-white/5 rounded-2xl p-6 sm:p-8 shadow-xl flex items-center justify-center min-h-[200px]">
                                <p className="text-gray-500 text-sm">Notification preferences are coming soon.</p>
                            </div>
                        </div>
                    )}

                    {activeTab === 'billing' && (
                        <div className="animate-in fade-in slide-in-from-right-4 duration-500 relative z-10 w-full">
                            <Billing />
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
