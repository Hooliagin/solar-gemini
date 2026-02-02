import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Settings, Sun, Moon, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Player from '../components/Player';
import Recorder from '../components/Recorder';
import DiaryList from '../components/DiaryList';
import CalendarView from '../components/CalendarView';
import { API_BASE_URL } from '../config';

export default function Dashboard() {
    const { session } = useAuth();
    const navigate = useNavigate();
    const [userName, setUserName] = useState('');
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [setupComplete, setSetupComplete] = useState(true);

    // Check Setup Status (Name, Voice, City)
    useEffect(() => {
        const checkSetup = async () => {
            if (!session?.access_token) return;
            try {
                const res = await fetch(`${API_BASE_URL}/settings/`, {
                    headers: { Authorization: `Bearer ${session.access_token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    setUserName(data.name || '');
                    const isComplete = !!(data.name && data.voice_id);
                    setSetupComplete(isComplete);
                }
            } catch (e) {
                console.error(e);
            }
        };
        checkSetup();
    }, [session]);

    const getTimeOfDay = () => {
        const hour = new Date().getHours();
        if (hour < 12) return { greeting: "Guten Morgen", icon: Sun };
        if (hour < 18) return { greeting: "Guten Tag", icon: Sun };
        return { greeting: "Guten Abend", icon: Moon };
    };

    const { greeting } = getTimeOfDay();

    const [latestBriefing, setLatestBriefing] = useState<any>(null);

    // Format Date for Header: "Mi., 28. Jan."
    const getFormattedDate = (isoString?: string) => {
        const date = isoString ? new Date(isoString) : new Date();
        return date.toLocaleDateString('de-DE', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    };

    const briefingTitle = latestBriefing
        ? `Ihr morgendliches Briefing für den ${getFormattedDate(latestBriefing.created_at)}`
        : "Ihr morgendliches Briefing";

    const briefingQuote = latestBriefing?.quote || "Wissen ist der Zinseszins der Neugier.";

    return (
        <div className="min-h-screen text-charcoal pb-32">

            <div className="max-w-[1400px] mx-auto px-8 md:px-16 py-12 md:py-24">
                {/* Header */}
                <header className="flex justify-between items-start mb-24 animate-fade-in relative z-20">
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center gap-3">
                            <span className="h-px w-12 bg-charcoal/30 block" />
                            <span className="text-xs uppercase tracking-[0.2em] text-warm-grey font-medium">{greeting}</span>
                        </div>
                        <h1 className="text-6xl md:text-8xl font-serif tracking-tighter leading-[0.9] mix-blend-difference text-charcoal">
                            {userName || 'Gast'}
                        </h1>
                        <div className="mt-6 flex gap-6">
                            <button
                                onClick={() => navigate('/weekly')}
                                className="text-xs font-medium uppercase tracking-[0.15em] text-gold hover:text-charcoal transition-colors flex items-center gap-2 group"
                            >
                                <span className="border-b border-gold group-hover:border-charcoal transition-colors">Zur Wochen-Vision</span>
                                <ArrowRight className="w-3 h-3 transform group-hover:translate-x-1 transition-transform" />
                            </button>
                        </div>
                    </div>

                    <button
                        onClick={() => navigate('/settings')}
                        className="group relative p-4 transition-all duration-500 hover:rotate-90"
                    >
                        <Settings strokeWidth={1} className="w-8 h-8 text-charcoal group-hover:text-gold transition-colors" />
                        {!setupComplete && (
                            <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                        )}
                    </button>
                </header>

                {/* Setup Widget (Conditional) */}
                <AnimatePresence>
                    {!setupComplete && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="mb-16 overflow-hidden"
                        >
                            <div
                                onClick={() => navigate('/settings')}
                                className="border-t border-b border-charcoal/10 py-8 flex items-center justify-between cursor-pointer group hover:bg-white/40 transition-colors"
                            >
                                <div className="flex items-center gap-6">
                                    <div className="w-12 h-12 flex items-center justify-center border border-charcoal/20">
                                        <AlertCircle strokeWidth={1} className="w-6 h-6 text-charcoal group-hover:text-gold transition-colors" />
                                    </div>
                                    <div>
                                        <h3 className="font-serif text-2xl mb-1 group-hover:italic transition-all">Einrichtung abschließen</h3>
                                        <p className="text-warm-grey text-sm tracking-wide">Konfigurieren Sie Name & Stimme</p>
                                    </div>
                                </div>
                                <ArrowRight strokeWidth={1} className="w-6 h-6 transform group-hover:translate-x-2 transition-transform duration-500" />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <main className="grid grid-cols-1 md:grid-cols-12 gap-x-12 gap-y-24">

                    {/* Main Grid Layout */}
                    <div className="col-span-1 md:col-span-8 space-y-12 animate-slide-up" style={{ animationDelay: '0.1s' }}>

                        {/* 01 Briefing Player */}
                        <div>
                            <div className="flex items-center gap-4 mb-8">
                                <span className="text-xs font-mono text-charcoal/40">01</span>
                                <h2 className="text-sm font-sans uppercase tracking-[0.2em] border-b border-gold pb-1">Morgendliches Briefing</h2>
                            </div>
                            <div className="card-luxury min-h-[300px] flex flex-col justify-between group hover:border-gold transition-colors duration-500">
                                <div className="mb-8">
                                    <h3 className="text-4xl font-serif mb-4 group-hover:translate-x-2 transition-transform duration-700 leading-tight">
                                        {briefingTitle}
                                    </h3>
                                    <p className="text-warm-grey font-serif italic max-w-md">"{briefingQuote}"</p>
                                </div>
                                <Player onBriefingLoaded={setLatestBriefing} />
                            </div>
                        </div>

                        {/* 02 Recorder */}
                        <div>
                            <div className="flex items-center gap-4 mb-8">
                                <span className="text-xs font-mono text-charcoal/40">02</span>
                                <h2 className="text-sm font-sans uppercase tracking-[0.2em] border-b border-transparent group-hover:border-gold pb-1 transition-colors">Tagebuch-Eintrag</h2>
                            </div>
                            <div className="card-luxury min-h-[300px] flex flex-col justify-between group hover:border-gold transition-colors duration-500">
                                <div className="mb-8">
                                    <h3 className="text-4xl font-serif mb-4 group-hover:translate-x-2 transition-transform duration-700">Audio-<br />Tagebuch</h3>
                                    <p className="text-warm-grey font-serif italic">Nehmen Sie Ihre Gedanken auf.</p>
                                </div>
                                <Recorder onUploadComplete={() => setRefreshTrigger(p => p + 1)} />
                            </div>
                        </div>

                    </div>

                    {/* Right Column: Calendar */}
                    <div className="col-span-1 md:col-span-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
                        {latestBriefing && latestBriefing.calendar_events && (
                            <CalendarView
                                events={JSON.parse(latestBriefing.calendar_events)}
                                isUpdating={false} // TODO: Add state
                                onUpdateErrors={async (newEvents) => {
                                    // Optimistic update would be good here, but for now simple
                                    console.log("Updating events:", newEvents);
                                    if (!session?.access_token || !latestBriefing.id) return;

                                    try {
                                        await fetch(`${API_BASE_URL}/briefings/${latestBriefing.id}/events`, {
                                            method: 'PUT',
                                            headers: {
                                                'Authorization': `Bearer ${session.access_token}`,
                                                'Content-Type': 'application/json'
                                            },
                                            body: JSON.stringify(newEvents)
                                        });
                                        // Silent success or toast
                                    } catch (e) {
                                        console.error("Failed to update events", e);
                                    }
                                }}
                                onExport={async () => {
                                    if (!session?.access_token || !latestBriefing.id) return;
                                    try {
                                        const res = await fetch(`${API_BASE_URL}/briefings/${latestBriefing.id}/export-calendar`, {
                                            method: 'POST',
                                            headers: {
                                                'Authorization': `Bearer ${session.access_token}`
                                            }
                                        });
                                        if (res.ok) {
                                            const data = await res.json();
                                            alert(data.message); // Simple alert for now, could be a toast
                                        } else {
                                            const err = await res.json();
                                            alert("Fehler beim Export: " + err.detail);
                                        }
                                    } catch (e) {
                                        console.error("Export failed", e);
                                        alert("Export fehlgeschlagen.");
                                    }
                                }}
                            />
                        )}
                        {(!latestBriefing || !latestBriefing.calendar_events) && (
                            <div className="card-luxury h-full flex items-center justify-center opacity-50">
                                <p className="text-xs font-serif text-charcoal/40">Keine Agenda verfügbar</p>
                            </div>
                        )}
                    </div>

                    {/* Recent History (Full Width) */}
                    <div className="col-span-1 md:col-span-12 mt-12 animate-slide-up" style={{ animationDelay: '0.3s' }}>
                        <div className="flex items-center gap-4 mb-8">
                            <span className="text-xs font-mono text-charcoal/40">03</span>
                            <h2 className="text-sm font-sans uppercase tracking-[0.2em]">Archiv</h2>
                        </div>
                        <div className="border-t border-charcoal/20 pt-8">
                            <DiaryList refreshTrigger={refreshTrigger} />
                        </div>
                    </div>

                </main>
            </div >
        </div >
    );
}
