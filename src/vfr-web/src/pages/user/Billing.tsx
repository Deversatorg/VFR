import { useState, useEffect } from 'react';
import { BillingApi, getApiErrorMessage } from '../../api/apiClients';
import { CreditCard, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { createLogger } from '../../lib/logger';

const logger = createLogger('VFR.Web.Billing');

interface Subscription {
    id: number;
    status: string;
    planName: string;
    currentPeriodEnd: string;
}

interface Plan {
    id: number;
    name: string;
    price: number;
    features: string[];
}

export default function Billing() {
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [plans, setPlans] = useState<Plan[]>([
        { id: 1, name: "Developer", price: 0, features: ["Watermarked Avatars", "1,000 API Requests/mo", "Community Support"] },
        { id: 2, name: "Commerce Pro", price: 299, features: ["HD 4K Neural Renders", "100,000 API Requests/mo", "Priority Engine Queue"] },
        { id: 3, name: "Enterprise", price: 999, features: ["Custom Try-On Models", "Unlimited Requests", "Dedicated Success Manager"] }
    ]);
    const [isLoading, setIsLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

    useEffect(() => {
        fetchBillingData();
    }, []);

    const fetchBillingData = async () => {
        setIsLoading(true);
        try {
            // Fetch subscription (returns mock or real data from .NET)
            const subRes = await BillingApi.getSubscription();
            const subDataWrapper = subRes.data;
            const sub = subDataWrapper?.data || subDataWrapper?.subscription || subDataWrapper;
            if (sub && typeof sub === 'object' && 'planName' in sub) {
                setSubscription(sub);
            }
            // Fetch dynamic plans (optional, falling back to static if fails)
            try {
                const planRes = await BillingApi.getPlans();
                const planDataWrapper = planRes.data;
                const plansArray = planDataWrapper?.items || planDataWrapper?.data?.items || planDataWrapper?.data || planDataWrapper?.plans || (Array.isArray(planDataWrapper) ? planDataWrapper : []);
                
                if (plansArray && plansArray.length > 0) {
                    setPlans(plansArray);
                }
            } catch {
                // Ignore dynamic plans error, stick to static defaults
            }
        } catch (err) {
            logger.error('Failed to load billing data.', undefined, err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubscribe = async (planId: number) => {
        setActionLoading(true);
        setMessage(null);
        const loadingToast = toast.loading("Redirecting to secure checkout...");
        try {
            const response = await BillingApi.checkout({ planId });
            const checkoutUrl = response.data?.url || response.data?.checkoutUrl || response.data?.data?.url || response.data?.data?.checkoutUrl;
            
            if (checkoutUrl && typeof checkoutUrl === 'string') {
                toast.dismiss(loadingToast);
                window.location.href = checkoutUrl;
            } else {
                toast.error("Checkout initiated, but no redirect URL was provided.");
                toast.dismiss(loadingToast);
                setMessage({ type: 'success', text: 'Checkout initiated, but no redirect URL was provided by the server.' });
                fetchBillingData(); // Refresh just in case it was a direct upgrade
            }
        } catch (err) {
            const errMsg = getApiErrorMessage(err, 'Failed to initialize checkout.');
            toast.error(errMsg);
            toast.dismiss(loadingToast);
            setMessage({ type: 'error', text: errMsg });
        } finally {
            setActionLoading(false);
        }
    };

    const handleCancel = async () => {
        if (!confirm("Are you sure you want to cancel your subscription?")) return;
        setActionLoading(true);
        setMessage(null);
        try {
            await BillingApi.cancelSubscription();
            setMessage({ type: 'success', text: 'Subscription cancelled.' });
            fetchBillingData();
        } catch (err) {
            setMessage({ type: 'error', text: getApiErrorMessage(err, 'Failed to cancel.') });
        } finally {
            setActionLoading(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex items-center justify-center min-h-[50vh]">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
                <h1 className="text-3xl font-semibold text-white tracking-tight mb-2">Billing & Plans</h1>
                <p className="text-gray-400">Manage your subscription and API quotas.</p>
            </div>

            {message && (
                <div className={`p-4 rounded-xl border flex items-start gap-3 ${message.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
                    {message.type === 'success' ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <XCircle className="w-5 h-5 shrink-0" />}
                    <p>{message.text}</p>
                </div>
            )}

            {/* Current Subscription Status */}
            <div className="bg-[#111111] border border-white/5 rounded-2xl p-6 sm:p-8">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                            <CreditCard className="w-6 h-6 text-primary" />
                        </div>
                        <div>
                            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">Current Plan</h3>
                            <div className="flex items-center gap-3">
                                <span className="text-2xl font-semibold text-white">
                                    {subscription ? subscription.planName : 'Free Tier'}
                                </span>
                                {subscription && subscription.status === 'active' && (
                                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20">Active</span>
                                )}
                            </div>
                        </div>
                    </div>

                    {subscription && subscription.status === 'active' && (
                        <button
                            onClick={handleCancel}
                            disabled={actionLoading}
                            className="px-4 py-2 border border-red-500/50 hover:bg-red-500/10 text-red-400 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                        >
                            Cancel Subscription
                        </button>
                    )}
                </div>
            </div>

            {/* Pricing Cards */}
            <h2 className="text-xl font-semibold text-white pt-4">Available Plans</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {(plans || []).map((plan: Plan) => {
                    const isActive = subscription?.planName === plan.name;
                    return (
                        <div key={plan.id} className={`bg-[#111111] border rounded-2xl p-6 sm:p-8 flex flex-col ${isActive ? 'border-primary shadow-[0_0_30px_rgba(19,91,236,0.15)] relative overflow-hidden' : 'border-white/5'}`}>
                            {isActive && (
                                <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-primary to-primary-light" />
                            )}
                            <h3 className="text-xl font-medium text-white mb-2">{plan.name}</h3>
                            <div className="flex items-baseline gap-1 mb-6">
                                <span className="text-4xl font-bold text-white">${plan.price}</span>
                                <span className="text-gray-400 text-sm">/mo</span>
                            </div>

                            <ul className="space-y-4 mb-8 flex-1">
                                {(plan.features || []).map((feature: string, idx: number) => (
                                    <li key={idx} className="flex items-start gap-3">
                                        <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                                        <span className="text-sm text-gray-300">{feature}</span>
                                    </li>
                                ))}
                            </ul>

                            <button
                                onClick={() => handleSubscribe(plan.id)}
                                disabled={actionLoading || isActive}
                                className={`w-full py-3 px-4 rounded-xl text-sm font-medium transition-all ${
                                    isActive 
                                        ? 'bg-white/5 text-gray-400 cursor-not-allowed border border-white/5' 
                                        : 'bg-primary hover:bg-primary-dark text-white shadow-lg shadow-primary/20'
                                }`}
                            >
                                {isActive ? 'Current Plan' : 'Subscribe'}
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
