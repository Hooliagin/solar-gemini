import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';
import { supabase } from '../lib/supabase';
import { ArrowLeft, Trash2, User, Calendar, MessageCircle, Shield, AlertTriangle, AlertCircle } from 'lucide-react';

interface UserData {
    user_id: string;
    name: string | null;
    telegram_linked: boolean;
    calendar_linked: boolean;
    is_admin: boolean;
    is_approved: boolean; // Added
    entry_count: number;
    briefing_count: number;
    created_at: string | null;
}

export default function AdminDashboard() {
    const { session } = useAuth();
    const navigate = useNavigate();
    const [users, setUsers] = useState<UserData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/admin/users`, {
                headers: {
                    Authorization: `Bearer ${session?.access_token}`,
                },
            });

            if (res.status === 403) {
                setError('Access denied. Admin privileges required.');
                setLoading(false);
                return;
            }

            if (!res.ok) throw new Error('Failed to fetch users');

            const data = await res.json();
            setUsers(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (userId: string) => {
        if (!confirm('Are you sure you want to delete this user and ALL their data?')) return;

        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                setUsers(users.filter(u => u.user_id !== userId));
            } else {
                alert('Failed to delete user');
            }
        } catch (error) {
            console.error(error);
        }
    };

    const approveUser = async (userId: string) => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/approve`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                // Update local state
                setUsers(users.map(u => u.user_id === userId ? { ...u, is_approved: true } : u));
            } else {
                alert('Failed to approve user');
            }
        } catch (error) {
            console.error(error);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-alabaster flex items-center justify-center">
                <div className="w-12 h-12 border-2 border-charcoal border-t-transparent animate-spin rounded-full" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-alabaster flex flex-col items-center justify-center gap-4 p-8">
                <AlertTriangle size={48} className="text-red-500" />
                <p className="text-charcoal text-lg">{error}</p>
                <button
                    onClick={() => navigate('/')}
                    className="px-6 py-2 bg-charcoal text-alabaster rounded-lg hover:bg-charcoal/80 transition"
                >
                    Go Back
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-alabaster p-6">
            {/* Header */}
            <div className="max-w-4xl mx-auto mb-8">
                <button
                    onClick={() => navigate('/')}
                    className="flex items-center gap-2 text-charcoal/60 hover:text-charcoal transition mb-4"
                >
                    <ArrowLeft size={20} />
                    <span>Back to Dashboard</span>
                </button>

                <div className="flex items-center gap-3">
                    <Shield className="text-charcoal" size={32} />
                    <h1 className="text-3xl font-serif text-charcoal">Admin Portal</h1>
                </div>
                <p className="text-charcoal/60 mt-2">Manage users and their data.</p>
            </div>

            {/* Users Table */}
            <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-lg overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-charcoal/5 border-b border-charcoal/10">
                            <tr>
                                <th className="text-left p-4 font-medium text-charcoal/80">User</th>
                                <th className="text-center p-4 font-medium text-charcoal/80">Status</th>
                                <th className="text-center p-4 font-medium text-charcoal/80">Telegram</th>
                                <th className="text-center p-4 font-medium text-charcoal/80">Calendar</th>
                                <th className="text-center p-4 font-medium text-charcoal/80">Entries</th>
                                <th className="text-center p-4 font-medium text-charcoal/80">Briefings</th>
                                <th className="text-right p-4 font-medium text-charcoal/80">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((user) => (
                                <tr key={user.user_id} className="border-b border-charcoal/5 hover:bg-charcoal/[0.02] transition">
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 bg-charcoal/10 rounded-full flex items-center justify-center">
                                                <User size={18} className="text-charcoal/60" />
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <p className="font-medium text-charcoal">{user.name || 'Unnamed'}</p>
                                                    {user.is_admin && (
                                                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">Admin</span>
                                                    )}
                                                </div>
                                                <p className="text-xs text-charcoal/40 font-mono">{user.user_id.slice(0, 8)}...</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-4 text-center">
                                        {!user.is_approved ? (
                                            <button
                                                onClick={() => approveUser(user.user_id)}
                                                className="px-2 py-1 bg-amber-500 text-white text-xs rounded hover:bg-amber-600 transition flex items-center gap-1 mx-auto"
                                            >
                                                <AlertCircle size={12} />
                                                Approve
                                            </button>
                                        ) : (
                                            <span className="text-xs text-green-600 font-medium">Active</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-center">
                                        <MessageCircle
                                            size={20}
                                            className={user.telegram_linked ? 'text-green-500 mx-auto' : 'text-charcoal/20 mx-auto'}
                                        />
                                    </td>
                                    <td className="p-4 text-center">
                                        <Calendar
                                            size={20}
                                            className={user.calendar_linked ? 'text-blue-500 mx-auto' : 'text-charcoal/20 mx-auto'}
                                        />
                                    </td>
                                    <td className="p-4 text-center text-charcoal/80">{user.entry_count}</td>
                                    <td className="p-4 text-center text-charcoal/80">{user.briefing_count}</td>
                                    <td className="p-4 text-right">
                                        {!user.is_admin && (
                                            <button
                                                onClick={() => setDeleteTarget(user.user_id)}
                                                className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
                                                title="Delete User"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {users.length === 0 && (
                    <div className="p-8 text-center text-charcoal/40">No users found.</div>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            {deleteTarget && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl">
                        <div className="flex items-center gap-3 mb-4">
                            <AlertTriangle className="text-red-500" size={28} />
                            <h2 className="text-xl font-serif text-charcoal">Confirm Deletion</h2>
                        </div>
                        <p className="text-charcoal/70 mb-6">
                            Are you sure you want to delete this user? This will permanently remove all their data including entries,
                            briefings, and settings. This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setDeleteTarget(null)}
                                className="px-4 py-2 text-charcoal/60 hover:text-charcoal transition"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleDelete(deleteTarget)}
                                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
                            >
                                Delete User
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
