import { useState, useEffect } from 'react';

import { useNavigate } from 'react-router-dom';
import { Settings, ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Player from '../components/Player';
import WeeklyCalendarView from '../components/WeeklyCalendarView';
import { API_BASE_URL } from '../config';

export default function WeeklyDashboard() {
    const { session } = useAuth();
    const navigate = useNavigate();
    // Check Setup
    useEffect(() => {
        const checkSetup = async () => {
            // Just verifying session
        };
        checkSetup();
    }, [session]);

    const [latestBriefing, setLatestBriefing] = useState<any>(null);
    const [usage, setUsage] = useState<{ weekly_used: number; weekly_limit: number } | null>(null);

    useEffect(() => {
        const fetchUsage = async () => {
            if (!session?.access_token) return;
            try {
                const res = await fetch(`${API_BASE_URL}/briefings/usage`, {
                    headers: { Authorization: `Bearer ${session.access_token}` }
                });
                if (res.ok) setUsage(await res.json());
            } catch (e) { console.error(e); }
        };
        fetchUsage();
    }, [session]);

    return (
        <div className="min-h-screen text-charcoal pb-32">
            <div className="max-w-[1400px] mx-auto px-8 md:px-16 py-12 md:py-24">

                {/* Header */}
                <header className="flex justify-between items-start mb-12 animate-fade-in relative z-20">
                    <button
                        onClick={() => navigate('/')}
                        className="group flex items-center gap-2 text-xs uppercase tracking-widest text-warm-grey hover:text-charcoal transition-colors mb-4"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Zurück zum Tag
                    </button>

                    <button
                        onClick={() => navigate('/settings')}
                        className="group relative p-4 transition-all duration-500 hover:rotate-90"
                    >
                        <Settings strokeWidth={1} className="w-8 h-8 text-charcoal group-hover:text-gold transition-colors" />
                    </button>
                </header>

                <div className="mb-16">
                    <div className="flex items-center gap-3 mb-4">
                        <span className="h-px w-12 bg-charcoal/30 block" />
                        <span className="text-xs uppercase tracking-[0.2em] text-gold font-medium">Weekly Vision</span>
                    </div>
                    <h1 className="text-5xl md:text-7xl font-serif tracking-tighter leading-[0.9] text-charcoal">
                        Deine Woche.
                    </h1>
                </div>

                <main className="grid grid-cols-1 md:grid-cols-12 gap-x-12 gap-y-24">

                    {/* Main Grid Layout */}
                    <div className="col-span-1 md:col-span-6 space-y-12 animate-slide-up" style={{ animationDelay: '0.1s' }}>

                        {/* 01 Briefing Player */}
                        <div>
                            <div className="flex items-center gap-4 mb-8">
                                <span className="text-xs font-mono text-charcoal/40">01</span>
                                <h2 className="text-sm font-sans uppercase tracking-[0.2em] border-b border-gold pb-1">Wochen-Briefing</h2>
                                {usage && (
                                    <span className="ml-auto text-[10px] uppercase tracking-widest text-warm-grey">
                                        {usage.weekly_used}/{usage.weekly_limit} diesen Monat
                                    </span>
                                )}
                            </div>
                            <div className="card-luxury min-h-[300px] flex flex-col justify-between group hover:border-gold transition-colors duration-500">
                                <div className="mb-8">
                                    <h3 className="text-3xl font-serif mb-4 group-hover:translate-x-2 transition-transform duration-700 leading-tight">
                                        Der Strategie-Check
                                    </h3>
                                    <p className="text-warm-grey font-serif italic max-w-md">
                                        "Reflektiere die letzte Woche, plane die kommende."
                                    </p>
                                </div>
                                <Player
                                    onBriefingLoaded={setLatestBriefing}
                                    briefingType="weekly"
                                />
                            </div>
                        </div>

                    </div>

                    {/* Right Column: Weekly Calendar */}
                    <div className="col-span-1 md:col-span-6 animate-slide-up" style={{ animationDelay: '0.2s' }}>
                        {latestBriefing && latestBriefing.calendar_events ? (
                            <WeeklyCalendarView
                                events={JSON.parse(latestBriefing.calendar_events)}
                            />
                        ) : (
                            <div className="card-luxury min-h-[300px] flex flex-col justify-center items-center opacity-60">
                                <p className="text-xs uppercase tracking-widest text-warm-grey">Erstelle zuerst dein Wochenbriefing</p>
                            </div>
                        )}
                    </div>

                </main>
            </div>
        </div>
    );
}
