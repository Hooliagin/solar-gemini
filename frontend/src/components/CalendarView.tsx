import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Edit2, Loader2, Upload } from 'lucide-react';

interface CalendarEvent {
    start: string;
    end?: string;
    name: string;
    calendar: string;
    id?: string;
    type?: 'fixed' | 'suggestion';
}

interface CalendarViewProps {
    events: CalendarEvent[];
    onUpdateErrors: (events: CalendarEvent[]) => void;
    onExport?: () => Promise<void>;
    isUpdating: boolean;
}

export default function CalendarView({ events: initialEvents, onUpdateErrors, onExport, isUpdating }: CalendarViewProps) {
    const [events, setEvents] = useState(initialEvents);
    const [editingIndex, setEditingIndex] = useState<number | null>(null);
    const [editValue, setEditValue] = useState("");
    const [editTime, setEditTime] = useState("");
    const [isExporting, setIsExporting] = useState(false);

    const handleEditStart = (index: number, event: CalendarEvent) => {
        setEditingIndex(index);
        setEditValue(event.name);
        // Extract time HH:MM
        let time = "All Day";
        if (event.start.includes('T')) {
            time = event.start.split('T')[1].substring(0, 5);
        } else if (event.start.includes(':')) {
            time = event.start.substring(0, 5);
        }
        setEditTime(time);
    };

    const handleSave = () => {
        if (editingIndex === null) return;

        const newEvents = [...events];
        const event = newEvents[editingIndex];

        // Update Name
        event.name = editValue;

        // Update Time (Simple handling)
        if (editTime !== "All Day") {
            if (event.start.includes('T')) {
                const datePart = event.start.split('T')[0];
                event.start = `${datePart}T${editTime}:00`;
            } else {
                event.start = editTime;
            }
        }

        setEvents(newEvents);
        setEditingIndex(null);
        onUpdateErrors(newEvents);
    };

    const handleExport = async () => {
        setIsExporting(true);
        if (onExport) {
            await onExport();
        }
        setIsExporting(false);
    };

    return (
        <div className="card-luxury relative min-h-[400px]">
            <div className="flex items-center justify-between gap-4 mb-8">
                <div className="flex items-center gap-4">
                    <span className="text-xs font-mono text-charcoal/40">04</span>
                    <h2 className="text-sm font-sans uppercase tracking-[0.2em] border-b border-gold pb-1">Tages-Agenda</h2>
                </div>
                {onExport && (
                    <button
                        onClick={handleExport}
                        disabled={isExporting}
                        className="flex items-center gap-2 text-[10px] uppercase tracking-widest hover:text-gold transition-colors disabled:opacity-50"
                        title="Vorschläge in echten Kalender übertragen"
                    >
                        {isExporting ? <Loader2 className="animate-spin w-3 h-3" /> : <Upload className="w-3 h-3" />}
                        <span>Export</span>
                    </button>
                )}
            </div>

            <div className="relative pl-4">
                {/* Vertical Line */}
                <div className="absolute left-[39px] top-4 bottom-4 w-px bg-gold/50" />

                <div className="space-y-8 relative z-10">
                    {events.length === 0 && (
                        <p className="text-warm-grey italic text-sm pl-12">Keine Termine für heute.</p>
                    )}

                    {events.map((event, index) => {
                        const isEditing = editingIndex === index;

                        // Parse Start
                        let startStr = "";
                        if (event.start.includes('T')) {
                            startStr = event.start.split('T')[1].substring(0, 5);
                        } else if (event.start.includes(':')) {
                            startStr = event.start.substring(0, 5);
                        }

                        // Parse End
                        let endStr = "";
                        if (event.end) {
                            if (event.end.includes('T')) {
                                endStr = event.end.split('T')[1].substring(0, 5);
                            } else if (event.end.includes(':')) {
                                endStr = event.end.substring(0, 5);
                            }
                        }

                        // Determine Dot Style
                        const isSuggestion = event.type === 'suggestion' || event.calendar === 'AI Suggestion';

                        return (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="group relative flex items-start gap-6 group"
                            >
                                {/* Dot */}
                                <div
                                    className={`absolute left-[21px] top-[9px] w-3 h-3 rounded-full border-2 border-gold z-20 transition-transform group-hover:scale-125 
                                    ${isSuggestion ? 'bg-[#F5F5F0]' : 'bg-gold'}`}
                                />

                                {/* Time */}
                                <div className="w-16 pt-1 text-right">
                                    {isEditing ? (
                                        <input
                                            value={editTime}
                                            onChange={(e) => setEditTime(e.target.value)}
                                            className="w-full bg-white/50 border-b border-charcoal/20 text-xs font-serif text-right focus:outline-none focus:border-gold"
                                            placeholder="HH:MM"
                                        />
                                    ) : (
                                        <div className="group/time cursor-pointer hover:text-gold transition-colors" onClick={() => handleEditStart(index, event)}>
                                            <span className="text-xs font-serif text-charcoal/60 leading-tight block">
                                                {startStr || "Ganztägig"}
                                                {endStr && <span className="block opacity-60">-{endStr}</span>}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 pt-0.5 min-w-0">
                                    {isEditing ? (
                                        <div className="flex items-center gap-2">
                                            <input
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                className="w-full bg-white/50 border-b border-charcoal/20 font-sans text-sm focus:outline-none focus:border-gold"
                                                autoFocus
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleSave();
                                                }}
                                            />
                                            <button
                                                onClick={handleSave}
                                                className="p-1 hover:bg-gold/10 rounded-full text-gold transition-colors"
                                            >
                                                <Check size={16} />
                                            </button>
                                        </div>
                                    ) : (
                                        <div
                                            className="group/item flex items-center justify-between cursor-pointer"
                                            onClick={() => handleEditStart(index, event)}
                                        >
                                            <h4 className={`font-sans text-charcoal group-hover:text-gold transition-colors truncate ${isSuggestion ? 'italic text-charcoal/80' : ''}`}>
                                                {event.name}
                                            </h4>
                                            <Edit2 size={12} className="opacity-0 group-hover/item:opacity-30 ml-2" />
                                        </div>
                                    )}
                                    <p className="text-[10px] text-warm-grey uppercase tracking-wider mt-0.5">{event.calendar}</p>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>
            </div>

            {isUpdating && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="absolute top-4 right-4 text-xs text-gold animate-pulse"
                >
                    Speichern...
                </motion.div>
            )}
        </div>
    );
}
