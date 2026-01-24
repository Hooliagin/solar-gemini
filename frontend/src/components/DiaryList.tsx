import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';
import { Calendar, FileText, Globe } from 'lucide-react';

interface Entry {
    id: number;
    created_at: string;
    transcript: string;
    language: string;
    summary?: string;
}

export default function DiaryList() {
    const [entries, setEntries] = useState<Entry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchEntries();
    }, []);

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

    if (loading) return <div className="text-center text-gray-500 py-4 animate-pulse">Lade Tagebuch...</div>;
    if (entries.length === 0) return null;

    return (
        <div className="space-y-4">
            {entries.map((entry) => (
                <div key={entry.id} className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-all">
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
                            <Calendar className="w-3 h-3" />
                            {new Date(entry.created_at).toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                        </div>
                        <div className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-gray-400 uppercase">
                            <Globe className="w-3 h-3" />
                            {entry.language || '??'}
                        </div>
                    </div>
                    {entry.transcript ? (
                        <p className="text-sm text-gray-300 line-clamp-3 italic">
                            "{entry.transcript}"
                        </p>
                    ) : (
                        <span className="text-xs text-gray-600 italic">(Kein Transkript)</span>
                    )}
                </div>
            ))}
        </div>
    );
}
