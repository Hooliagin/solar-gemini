import React, { useEffect, useState } from 'react';
import { Plus, X, Sparkles, TrendingUp } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

interface Interest {
    id: number;
    topic: string;
}

// Suggestion tags for quick adding
const SUGGESTIONS = ['KI', 'Fußball', 'Aktien', 'Krypto', 'Gaming', 'Startups', 'Klimawandel'];

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

    const addInterest = async (topic: string) => {
        if (!topic.trim()) return;

        setLoading(true);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/interests/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ topic: topic.trim() })
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

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        addInterest(newTopic);
    };

    // Filter out already added suggestions
    const availableSuggestions = SUGGESTIONS.filter(
        s => !interests.some(i => i.topic.toLowerCase() === s.toLowerCase())
    );

    return (
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden">
            {/* Background Decoration */}
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-gradient-to-br from-pink-500/20 to-purple-500/20 rounded-full blur-2xl" />

            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-pink-500 to-purple-500 shadow-lg shadow-pink-500/20">
                    <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h2 className="text-lg font-semibold text-white">
                        Deine Interessen
                    </h2>
                    <p className="text-xs text-gray-500">Personalisiere dein Briefing</p>
                </div>
            </div>

            {/* Interest Tags */}
            <div className="flex flex-wrap gap-2 mb-6 min-h-[3rem]">
                {interests.map(interest => (
                    <div
                        key={interest.id}
                        className="group flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-pink-500/20 to-purple-500/20 border border-pink-500/30 hover:border-pink-400 transition-all"
                    >
                        <span className="text-sm text-pink-200">#{interest.topic}</span>
                        <button
                            onClick={() => deleteInterest(interest.id)}
                            className="opacity-50 group-hover:opacity-100 p-0.5 hover:bg-white/10 rounded-full transition-all text-pink-200 hover:text-red-400"
                        >
                            <X className="w-3 h-3" />
                        </button>
                    </div>
                ))}
                {interests.length === 0 && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 italic">
                        <Sparkles className="w-4 h-4" />
                        Füge Themen hinzu für personalisierte News
                    </div>
                )}
            </div>

            {/* Quick Suggestions */}
            {availableSuggestions.length > 0 && (
                <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">Schnell hinzufügen:</p>
                    <div className="flex flex-wrap gap-1.5">
                        {availableSuggestions.map(suggestion => (
                            <button
                                key={suggestion}
                                onClick={() => addInterest(suggestion)}
                                disabled={loading}
                                className="px-2.5 py-1 text-xs rounded-full border border-white/10 text-gray-400 hover:border-purple-500/50 hover:text-purple-300 hover:bg-purple-500/10 transition-all disabled:opacity-50"
                            >
                                + {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Add Custom Topic */}
            <form onSubmit={handleSubmit} className="relative">
                <input
                    type="text"
                    value={newTopic}
                    onChange={(e) => setNewTopic(e.target.value)}
                    placeholder="Eigenes Thema hinzufügen..."
                    className="input-field w-full pr-12 text-sm"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !newTopic.trim()}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 p-2 bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-400 hover:to-purple-400 rounded-lg transition-all disabled:opacity-30 disabled:hover:from-pink-500 disabled:hover:to-purple-500 shadow-lg shadow-pink-500/20"
                >
                    <Plus className="w-4 h-4 text-white" />
                </button>
            </form>
        </div>
    );
}
