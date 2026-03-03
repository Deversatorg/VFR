import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authClient } from '../api/apiClients';

export default function Register() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await authClient.post('/auth/register', { email, password });
            setSuccess(true);
            setTimeout(() => navigate('/login'), 2000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Registration failed');
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-950 text-white">
            <div className="w-full max-w-md p-8 bg-gray-900 border border-gray-800 rounded-2xl shadow-xl">
                <h2 className="text-3xl font-bold text-center mb-8">Create Account</h2>
                {error && <div className="p-3 mb-4 text-sm text-red-400 bg-red-900/20 border border-red-500/20 rounded-lg">{error}</div>}
                {success && <div className="p-3 mb-4 text-sm text-green-400 bg-green-900/20 border border-green-500/20 rounded-lg">Registration successful! Redirecting to login...</div>}
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Email</label>
                        <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Password</label>
                        <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all" />
                    </div>
                    <button type="submit" disabled={success} className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors">
                        Register
                    </button>
                    <p className="text-center text-gray-500 mt-4 text-sm">
                        Already have an account? <a href="/login" className="text-blue-400 hover:underline">Sign In</a>
                    </p>
                </form>
            </div>
        </div>
    );
}
