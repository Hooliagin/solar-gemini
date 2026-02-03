import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';
import { Check } from 'lucide-react';

interface Calendar {
    id: string;
    name: string;
    primary: boolean;
    color?: string;
}

interface CalendarSelectorProps {
    selectedIds: string[];
    onChange: (ids: string[]) => void;
}

export default function CalendarSelector({ selectedIds, onChange }: CalendarSelectorProps) {
    const [calendars, setCalendars] = useState<Calendar[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchCalendars = async () => {
            try {
                const token = (await supabase.auth.getSession()).data.session?.access_token;
                if (!token) return;

                const res = await fetch(`${API_BASE_URL}/settings/calendars`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();
                    setCalendars(data);

                    // Initial sync: If selectedIds is empty but we have data,
                    // specific logic might be needed?
                    // Actually, the parent keeps the "source of truth".
                    // But if selectedIds is EMPTY array, it might mean "ALL" (default behavior) or "NONE".
                    // My backend logic: Empty/Null -> All.
                    // But frontend state might want to be explicit.
                    // If backend sends empty list for selected_calendars, it means None filters (All).
                    // So we should visually toggle ALL ON if selectedIds is empty initially?
                    // Let's rely on what backend returns for "selected" property in /calendars?
                    // But /calendars reflects saved state.
                    // Parent state reflects *current* unsaved state.
                    // So we just render toggles based on props.
                }
            } catch (err) {
                console.error("Failed to load calendars", err);
            } finally {
                setLoading(false);
            }
        };

        fetchCalendars();
    }, []);

    const toggleCalendar = (id: string) => {
        let newSelection = [...selectedIds];
        if (newSelection.includes(id)) {
            newSelection = newSelection.filter(c => c !== id);
        } else {
            newSelection.push(id);
        }
        onChange(newSelection);
    };

    if (loading) {
        return <div className="text-xs text-warm-grey animate-pulse">Lade Kalender...</div>;
    }

    if (calendars.length === 0) {
        return <div className="text-xs text-warm-grey italic">Keine Kalender gefunden.</div>;
    }

    return (
        <div className="mt-8 pt-8 border-t border-charcoal/10 space-y-4 animate-fade-in">
            <h4 className="text-xs uppercase tracking-widest text-warm-grey mb-4">Aktive Kalender</h4>
            <div className="grid grid-cols-1 gap-2">
                {calendars.map((cal) => {
                    // Logic: If selectedIds is empty, it means DEFAULT (ALL). 
                    // But usually explicit is better for UI.
                    // Let's assume parent handles "if empty then treated as all" or passes full list if default.
                    // Actually, looking at SettingsPanel logic which I'll write:
                    // I will initialize selectedIds from backend string. If null, I might initialize with ALL IDs.

                    const isSelected = selectedIds.includes(cal.id);

                    return (
                        <button
                            key={cal.id}
                            onClick={() => toggleCalendar(cal.id)}
                            className={`
                                w-full flex items-center justify-between p-3 border transition-all duration-300
                                ${isSelected
                                    ? 'bg-alabaster border-charcoal/40'
                                    : 'bg-transparent border-transparent hover:border-charcoal/10 text-charcoal/50'
                                }
                            `}
                        >
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div
                                    className={`w-2 h-2 rounded-full flex-shrink-0 ${isSelected ? 'opacity-100' : 'opacity-30'}`}
                                    style={{ backgroundColor: cal.color || '#000' }}
                                />
                                <span className={`font-serif truncate ${isSelected ? 'text-charcoal' : 'text-warm-grey'}`}>
                                    {cal.name}
                                </span>
                                {cal.primary && (
                                    <span className="text-[10px] uppercase font-sans tracking-wider opacity-40 border border-charcoal/20 px-1 rounded">
                                        Primär
                                    </span>
                                )}
                            </div>

                            <div className={`
                                w-5 h-5 border flex items-center justify-center transition-colors
                                ${isSelected ? 'bg-charcoal border-charcoal text-alabaster' : 'border-charcoal/20'}
                            `}>
                                {isSelected && <Check className="w-3 h-3" />}
                            </div>
                        </button>
                    );
                })}
            </div>
            <p className="text-[10px] text-warm-grey mt-2">
                Nur ausgewählte Kalender werden für das tägliche Briefing analysiert.
            </p>
        </div>
    );
}
