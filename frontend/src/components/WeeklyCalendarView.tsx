import { useMemo } from 'react';

interface CalendarEvent {
    start: string;
    end?: string;
    name: string;
    calendar: string;
    type?: 'fixed' | 'suggestion';
}

interface WeeklyCalendarViewProps {
    events: CalendarEvent[];
}

export default function WeeklyCalendarView({ events }: WeeklyCalendarViewProps) {
    // Group events by Date
    const groupedEvents = useMemo(() => {
        const groups: Record<string, CalendarEvent[]> = {};

        events.forEach(event => {
            let dateStr = "Unknown";
            if (event.start.includes("T")) {
                dateStr = event.start.split("T")[0]; // YYYY-MM-DD
            } else {
                // Heuristic for simple dates if necessary
                dateStr = "Today";
            }

            if (!groups[dateStr]) groups[dateStr] = [];
            groups[dateStr].push(event);
        });

        // Sort dates
        return Object.keys(groups).sort().map(date => ({
            date,
            events: groups[date].sort((a, b) => a.start.localeCompare(b.start))
        }));
    }, [events]);

    // Format Date helper
    const formatDate = (dateStr: string) => {
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'short' });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="card-luxury relative min-h-[400px]">
            <div className="flex items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-4">
                    <span className="text-xs font-mono text-charcoal/40">05</span>
                    <h2 className="text-sm font-sans uppercase tracking-[0.2em] border-b border-gold pb-1">Wochen-Vision</h2>
                </div>
            </div>

            <div className="space-y-8 pl-2">
                {groupedEvents.length === 0 && (
                    <p className="text-warm-grey italic text-sm">Keine Woche geplant.</p>
                )}

                {groupedEvents.map((group) => (
                    <div key={group.date} className="relative">
                        {/* Date Header */}
                        <div className="sticky top-0 bg-[#F5F5F0] z-20 py-2 border-b border-charcoal/10 mb-4">
                            <h3 className="font-serif text-charcoal text-lg">{formatDate(group.date)}</h3>
                        </div>

                        <div className="space-y-4 pl-4 border-l border-gold/30">
                            {group.events.map((event, index) => {
                                // Parse Time
                                let timeStr = "All Day";
                                if (event.start.includes("T")) {
                                    timeStr = event.start.split("T")[1].slice(0, 5);
                                }

                                const isSuggestion = event.type === 'suggestion';

                                return (
                                    <div key={index} className="flex gap-4 items-start group">
                                        <div className="w-12 text-xs font-mono text-warm-grey pt-1">{timeStr}</div>
                                        <div>
                                            <div className={`font-sans text-sm ${isSuggestion ? 'italic text-charcoal/80' : 'text-charcoal'}`}>
                                                {event.name}
                                            </div>
                                            {isSuggestion && (
                                                <span className="text-[10px] text-gold uppercase tracking-wider">Vorschlag</span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
