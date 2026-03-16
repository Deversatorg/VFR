import { useState, useEffect } from 'react';
import { AdminApi } from '../api/apiClients';
import { ShieldAlert, Trash2, Search, Loader2 } from 'lucide-react';

interface User {
    id: number;
    firstName: string;
    lastName: string;
    email: string;
    registeredAt: string;
    isBlocked: boolean;
}

export default function AdminDashboard() {
    const [users, setUsers] = useState<User[]>([]);
    const [admins, setAdmins] = useState<User[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeTab, setActiveTab] = useState<'users' | 'admins'>('users');

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab]);

    const fetchData = async (search = searchQuery) => {
        setIsLoading(true);
        try {
            const params = { limit: 50, search: search || undefined };
            if (activeTab === 'users') {
                const res = await AdminApi.getUsers(params);
                const data = res.data;
                const usersArray = data?.items || data?.data?.items || data?.data || data?.users || (Array.isArray(data) ? data : []);
                setUsers(usersArray);
            } else {
                const res = await AdminApi.getAdmins(params);
                const data = res.data;
                const adminsArray = data?.items || data?.data?.items || data?.data || data?.admins || (Array.isArray(data) ? data : []);
                setAdmins(adminsArray);
            }
        } catch (error) {
            console.error("Failed to fetch admin data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        fetchData(searchQuery);
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to fully delete this user?")) return;
        try {
            await AdminApi.deleteUser(id);
            if (activeTab === 'users') {
                setUsers(prev => prev.filter(u => u.id !== id));
            } else {
                setAdmins(prev => prev.filter(u => u.id !== id));
            }
        } catch (error) {
            alert("Delete failed.");
        }
    };

    const dataSet = activeTab === 'users' ? users : admins;

    return (
        <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center justify-center">
                            <ShieldAlert className="w-5 h-5 text-red-500" />
                        </div>
                        <h1 className="text-3xl font-semibold text-white tracking-tight">System Admin</h1>
                    </div>
                    <p className="text-gray-400">Manage all registered accounts securely.</p>
                </div>

                <div className="flex bg-[#111111] p-1 rounded-xl border border-white/5">
                    <button
                        onClick={() => setActiveTab('users')}
                        className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'users' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-white'}`}
                    >
                        Standard Users
                    </button>
                    <button
                        onClick={() => setActiveTab('admins')}
                        className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'admins' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-white'}`}
                    >
                        Administrators
                    </button>
                </div>
            </div>

            <div className="bg-[#111111] border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
                {/* Toolbar */}
                <div className="p-4 border-b border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <h2 className="text-lg font-medium text-white">{activeTab === 'users' ? 'Registered Users' : 'Super Admins'}</h2>
                    
                    <form onSubmit={handleSearch} className="relative w-full sm:w-auto">
                        <Search className="w-4 h-4 text-gray-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Search by email..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full sm:w-64 pl-10 pr-4 py-2 bg-[#050505] border border-white/10 rounded-xl text-sm text-white placeholder-gray-600 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                        />
                    </form>
                </div>

                {/* Table */}
                <div className="w-full overflow-x-auto">
                    <table className="w-full text-left text-sm text-gray-400">
                        <thead className="text-xs uppercase bg-[#0a0a0a] text-gray-500 border-b border-white/5">
                            <tr>
                                <th scope="col" className="px-6 py-4 font-medium tracking-wider">ID</th>
                                <th scope="col" className="px-6 py-4 font-medium tracking-wider">Email</th>
                                <th scope="col" className="px-6 py-4 font-medium tracking-wider hidden sm:table-cell">Registered</th>
                                <th scope="col" className="px-6 py-4 font-medium tracking-wider">Status</th>
                                <th scope="col" className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-12 text-center">
                                        <Loader2 className="w-6 h-6 text-primary animate-spin mx-auto" />
                                    </td>
                                </tr>
                            ) : dataSet.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                                        No users found matching your criteria.
                                    </td>
                                </tr>
                            ) : (
                                dataSet.map((user) => (
                                    <tr key={user.id} className="border-b border-white/5 bg-[#111111] hover:bg-[#151515] transition-colors">
                                        <td className="px-6 py-4 font-mono text-xs">{user.id}</td>
                                        <td className="px-6 py-4 font-medium text-white">{user.email}</td>
                                        <td className="px-6 py-4 hidden sm:table-cell text-xs">{new Date(user.registeredAt).toLocaleDateString()}</td>
                                        <td className="px-6 py-4">
                                            {user.isBlocked ? (
                                                <span className="px-2 py-1 rounded-md bg-red-500/10 text-red-400 text-xs font-medium">Blocked</span>
                                            ) : (
                                                <span className="px-2 py-1 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-medium">Active</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button 
                                                onClick={() => handleDelete(user.id)}
                                                className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                                title="Delete User"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
