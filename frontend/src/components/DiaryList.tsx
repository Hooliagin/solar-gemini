import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';
// Imports removed

interface Entry {
    id: number;
    created_at: string;
    transcript: string;
    language: string;
    summary?: string;
}

export default function DiaryList({ refreshTrigger }: { refreshTrigger?: number }) {
    const [entries, setEntries] = useState<Entry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchEntries();
    }, [refreshTrigger]);

    const fetchEntries = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;

            const res = await fetch(`${API_BASE_URL}/entries/`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                setEntries(data);
            }
        } catch (error) {
            console.error('Failed to fetch entries', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="text-xs uppercase tracking-widest text-warm-grey animate-pulse">Loading Archives...</div>;
    if (entries.length === 0) return <div className="text-sm font-serif italic text-warm-grey">No entries found.</div>;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {entries.map((entry) => (
                <div key={entry.id} className="group border-t border-charcoal/10 pt-4 hover:border-gold transition-colors duration-500">
                    <div className="flex items-center justify-between mb-3 opacity-60 group-hover:opacity-100 transition-opacity">
                        <span className="font-mono text-[10px] text-charcoal">
                            {new Date(entry.created_at).toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: '2-digit' })}
                        </span>
                        <span className="text-[10px] uppercase tracking-widest text-warm-grey">
                            {entry.language || 'EN'}
                        </span>
                    </div>
                    {entry.transcript ? (
                        <p className="font-serif text-lg leading-relaxed text-charcoal line-clamp-3 group-hover:line-clamp-none transition-all">
                            "{entry.transcript}"
                        </p>
                    ) : (
                        <span className="text-xs text-warm-grey italic">(No transcript available)</span>
                    )}
                </div>
            ))}
        </div>
    );
}
