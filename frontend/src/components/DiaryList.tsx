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

import { Edit2, Check, X } from 'lucide-react';

export default function DiaryList({ refreshTrigger }: { refreshTrigger?: number }) {
    const [entries, setEntries] = useState<Entry[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editText, setEditText] = useState("");

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

    const startEditing = (entry: Entry) => {
        setEditingId(entry.id);
        setEditText(entry.transcript || "");
    };

    const cancelEditing = () => {
        setEditingId(null);
        setEditText("");
    };

    const saveEdit = async (id: number) => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;

            const res = await fetch(`${API_BASE_URL}/entries/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ transcript: editText })
            });

            if (res.ok) {
                // Update local state
                setEntries(entries.map(e => e.id === id ? { ...e, transcript: editText } : e));
                setEditingId(null);
            } else {
                alert("Fehler beim Speichern");
            }
        } catch (error) {
            console.error("Save failed", error);
            alert("Speichern fehlgeschlagen");
        }
    };

    if (loading) return <div className="text-xs uppercase tracking-widest text-warm-grey animate-pulse">Lade Archiv...</div>;
    if (entries.length === 0) return <div className="text-sm font-serif italic text-warm-grey">Keine Einträge gefunden.</div>;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {entries.map((entry) => (
                <div key={entry.id} className="group border-t border-charcoal/10 pt-4 hover:border-gold transition-colors duration-500 relative">
                    <div className="flex items-center justify-between mb-3">
                        <div className="opacity-60 group-hover:opacity-100 transition-opacity flex flex-col">
                            <span className="font-mono text-[10px] text-charcoal">
                                {new Date(entry.created_at).toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' })}
                            </span>
                            <span className="text-[10px] uppercase tracking-widest text-warm-grey">
                                {entry.language || 'EN'}
                            </span>
                        </div>

                        {/* Edit Controls */}
                        {editingId === entry.id ? (
                            <div className="flex gap-2">
                                <button onClick={() => saveEdit(entry.id)} className="p-1 hover:text-green-600 transition-colors"><Check className="w-4 h-4" /></button>
                                <button onClick={cancelEditing} className="p-1 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                            </div>
                        ) : (
                            <button
                                onClick={() => startEditing(entry)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity p-2 hover:bg-charcoal/5 rounded-full"
                                title="Bearbeiten"
                            >
                                <Edit2 className="w-3 h-3 text-charcoal" />
                            </button>
                        )}
                    </div>

                    {editingId === entry.id ? (
                        <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            className="w-full h-48 p-2 text-sm font-serif border border-gold focus:outline-none focus:ring-1 focus:ring-gold bg-alabaster resize-none"
                            autoFocus
                        />
                    ) : (
                        entry.transcript ? (
                            <p className="font-serif text-lg leading-relaxed text-charcoal line-clamp-3 group-hover:line-clamp-none transition-all whitespace-pre-wrap">
                                "{entry.transcript}"
                            </p>
                        ) : (
                            <span className="text-xs text-warm-grey italic">(Kein Transkript verfügbar)</span>
                        )
                    )}
                </div>
            ))}
        </div>
    );
}
