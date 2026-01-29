
import { useState, useEffect } from 'react';
import { Plus, X, Loader2 } from 'lucide-react';
import { API_BASE_URL } from '../config';
import { useAuth } from '../context/AuthContext';

interface Habit {
    id: number;
    name: string;
    description?: string;
    preferred_time: string;
    duration_minutes: number;
}

export default function HabitManager() {
    const { session } = useAuth();
    const [habits, setHabits] = useState<Habit[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    // Form State
    const [name, setName] = useState("");
    const [desc, setDesc] = useState("");
    const [time, setTime] = useState("any");
    const [duration, setDuration] = useState("30");

    useEffect(() => {
        if (session?.user?.id) {
            fetchHabits();
        }
    }, [session]);

    const fetchHabits = async () => {
        if (!session?.user?.id) return;
        try {
            // Note: In a real app we would rely on the JWT token to identify the user on the backend.
            // But currently the backend might be filtering by a query param or just returning all if not specified? 
            // Let's check if the backend supports filtering by user_id in the GET request or if we need to pass it.
            // Assuming for now we just call GET and maybe the backend needs to be updated to filter by token.
            // But wait, the previous code didn't pass user_id in GET. 
            // If the backend returns ALL habits, that's a security risk, but for now let's just make sure we CREATE with the right ID.

            // Ideally we pass the token:
            const res = await fetch(`${API_BASE_URL}/habits/?user_id=${session.user.id}`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setHabits(data);
            }
        } catch (error) {
            console.error("Failed to fetch habits", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!session?.user?.id) return;

        setIsSaving(true);
        try {
            const res = await fetch(`${API_BASE_URL}/habits/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    name,
                    description: desc,
                    preferred_time: time,
                    duration_minutes: parseInt(duration),
                    user_id: session.user.id
                })
            });

            if (res.ok) {
                const newHabit = await res.json();
                setHabits([...habits, newHabit]);
                setName("");
                setDesc("");
            }
        } catch (error) {
            console.error("Failed to add habit", error);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!window.confirm("Habit löschen?")) return;
        try {
            await fetch(`${API_BASE_URL}/habits/${id}`, { method: 'DELETE' });
            setHabits(habits.filter(h => h.id !== id));
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="space-y-12">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                {/* List */}
                <div className="space-y-4">
                    <h3 className="font-serif text-lg">Aktive Gewohnheiten</h3>
                    {isLoading ? (
                        <div className="text-warm-grey">Lade...</div>
                    ) : habits.length === 0 ? (
                        <p className="text-warm-grey italic text-sm">Keine Gewohnheiten definiert.</p>
                    ) : (
                        <ul className="space-y-3">
                            {habits.map(habit => (
                                <li key={habit.id} className="flex items-center justify-between group p-3 border border-charcoal/5 rounded-sm hover:border-gold/50 transition-colors bg-white/40">
                                    <div>
                                        <div className="font-sans text-sm">{habit.name}</div>
                                        <div className="text-xs text-warm-grey font-mono mt-0.5">
                                            {habit.duration_minutes}m • {habit.preferred_time}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(habit.id)}
                                        className="text-warm-grey hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity p-2"
                                    >
                                        <X size={14} />
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Form */}
                <div>
                    <h3 className="font-serif text-lg mb-6">Neue Gewohnheit</h3>
                    <form onSubmit={handleAdd} className="space-y-6">
                        <div>
                            <label className="block text-xs uppercase tracking-[0.1em] text-warm-grey mb-2">Name</label>
                            <input
                                value={name} onChange={e => setName(e.target.value)}
                                className="w-full bg-transparent border-b border-charcoal/20 py-2 font-sans focus:outline-none focus:border-gold placeholder-charcoal/20"
                                placeholder="z.B. Morning Run"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-xs uppercase tracking-[0.1em] text-warm-grey mb-2">Kontext / Beschreibung</label>
                            <input
                                value={desc} onChange={e => setDesc(e.target.value)}
                                className="w-full bg-transparent border-b border-charcoal/20 py-2 font-sans focus:outline-none focus:border-gold placeholder-charcoal/20"
                                placeholder="z.B. Im Park, nur wenn kein Regen"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-6">
                            <div>
                                <label className="block text-xs uppercase tracking-[0.1em] text-warm-grey mb-2">Dauer (Min)</label>
                                <input
                                    type="number"
                                    value={duration} onChange={e => setDuration(e.target.value)}
                                    className="w-full bg-transparent border-b border-charcoal/20 py-2 font-sans focus:outline-none focus:border-gold"
                                    min="5" step="5"
                                />
                            </div>
                            <div>
                                <label className="block text-xs uppercase tracking-[0.1em] text-warm-grey mb-2">Zeitfenster</label>
                                <select
                                    value={time} onChange={e => setTime(e.target.value)}
                                    className="w-full bg-transparent border-b border-charcoal/20 py-2 font-sans focus:outline-none focus:border-gold text-sm"
                                >
                                    <option value="any">egal</option>
                                    <option value="morning">Morgens</option>
                                    <option value="afternoon">Mittags</option>
                                    <option value="evening">Abends</option>
                                </select>
                            </div>
                        </div>

                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={isSaving || !name}
                                className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] hover:text-gold transition-colors disabled:opacity-50"
                            >
                                {isSaving ? <Loader2 className="animate-spin w-4 h-4" /> : <Plus className="w-4 h-4" />}
                                <span>Hinzufügen</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
