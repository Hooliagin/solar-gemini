import React, { useEffect, useState } from 'react';
import { Plus, X, Hash } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

interface Interest {
    id: number;
    topic: string;
}

export default function InterestManager() {
    const [interests, setInterests] = useState<Interest[]>([]);
    const [newTopic, setNewTopic] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchInterests();
    }, []);

    const fetchInterests = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/interests/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                setInterests(await res.json());
            }
        } catch (error) {
            console.error('Failed to fetch interests', error);
        }
    };

    const addInterest = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTopic.trim()) return;

        setLoading(true);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/interests/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ topic: newTopic })
            });

            if (res.ok) {
                setNewTopic('');
                fetchInterests();
            }
        } catch (error) {
            console.error('Failed to add interest', error);
        } finally {
            setLoading(false);
        }
    };

    const deleteInterest = async (id: number) => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            await fetch(`${API_BASE_URL}/interests/${id}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });
            setInterests(interests.filter(i => i.id !== id));
        } catch (error) {
            console.error('Failed to delete interest', error);
        }
    };

    return (
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                <Hash className="w-24 h-24 text-white/5 -rotate-12" />
            </div>

            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-pink-400 to-purple-400">
                    Your Interests
                </span>
            </h2>

            <div className="flex flex-wrap gap-2 mb-6">
                {interests.map(interest => (
                    <div key={interest.id} className="group/chip flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:border-purple-500/50 transition-all">
                        <span className="text-sm text-gray-300">#{interest.topic}</span>
                        <button
                            onClick={() => deleteInterest(interest.id)}
                            className="opacity-0 group-hover/chip:opacity-100 p-0.5 hover:bg-white/10 rounded-full transition-all text-gray-400 hover:text-red-400"
                        >
                            <X className="w-3 h-3" />
                        </button>
                    </div>
                ))}
                {interests.length === 0 && (
                    <p className="text-sm text-gray-500 italic">No interests added yet. Add topics to personalize your news.</p>
                )}
            </div>

            <form onSubmit={addInterest} className="relative">
                <input
                    type="text"
                    value={newTopic}
                    onChange={(e) => setNewTopic(e.target.value)}
                    placeholder="Add topic (e.g. AI, Formula 1)..."
                    className="input-field w-full pr-12 text-sm"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !newTopic.trim()}
                    className="absolute right-1 top-1 p-2 bg-white/10 hover:bg-purple-500 hover:text-white rounded-lg transition-all disabled:opacity-50 disabled:hover:bg-transparent"
                >
                    <Plus className="w-4 h-4" />
                </button>
            </form>
        </div>
    );
}
