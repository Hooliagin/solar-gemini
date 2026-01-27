import React, { useEffect, useState } from 'react';
import { Plus, X, TrendingUp } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

interface Interest {
    id: number;
    topic: string;
}

const SUGGESTIONS = ['AI', 'Football', 'Stocks', 'Crypto', 'Gaming', 'Startups', 'Climate'];

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
        if (interests.length >= 10) {
            alert("Maximum 10 interests allowed.");
            return;
        }

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

    const availableSuggestions = SUGGESTIONS.filter(
        s => !interests.some(i => i.topic.toLowerCase() === s.toLowerCase())
    );

    return (
        <div className="card-luxury relative">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8 opacity-60">
                <TrendingUp strokeWidth={1} className="w-5 h-5" />
                <div className="uppercase text-xs tracking-widest">
                    Ihre Interessen <span className="text-warm-grey">({interests.length}/10)</span>
                </div>
            </div>

            {/* Interest Tags */}
            <div className="flex flex-wrap gap-3 mb-8">
                {interests.map(interest => (
                    <div
                        key={interest.id}
                        className="group flex items-center gap-3 px-4 py-2 border border-charcoal bg-white hover:bg-charcoal hover:text-white transition-all duration-300 cursor-default"
                    >
                        <span className="font-serif italic text-lg">#{interest.topic}</span>
                        <button
                            onClick={() => deleteInterest(interest.id)}
                            className="opacity-40 group-hover:opacity-100 hover:text-red-400 transition-opacity"
                        >
                            <X className="w-3 h-3" />
                        </button>
                    </div>
                ))}
                {interests.length === 0 && (
                    <div className="text-sm text-warm-grey font-serif italic">
                        Noch keine Themen. Fügen Sie welche hinzu, um Ihr Briefing zu personalisieren.
                    </div>
                )}
            </div>

            {/* Quick Suggestions */}
            {availableSuggestions.length > 0 && (
                <div className="mb-8 border-t border-charcoal/10 pt-4">
                    <p className="text-xs uppercase tracking-widest text-warm-grey mb-3">Schnell hinzufügen</p>
                    <div className="flex flex-wrap gap-2">
                        {availableSuggestions.map(suggestion => (
                            <button
                                key={suggestion}
                                onClick={() => addInterest(suggestion)}
                                disabled={loading}
                                className="px-3 py-1 text-xs border border-charcoal/20 hover:border-charcoal hover:bg-charcoal/5 transition-colors disabled:opacity-50"
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
                    className="input-luxury pr-12 text-lg font-serif"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !newTopic.trim()}
                    className="absolute right-0 top-1/2 -translate-y-1/2 text-charcoal disabled:opacity-30 hover:text-gold transition-colors"
                >
                    <Plus strokeWidth={1} className="w-6 h-6" />
                </button>
            </form>
        </div>
    );
}
