import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';
import { supabase } from '../lib/supabase';
import { Play, RefreshCw, Clock, Sparkles, Volume2 } from 'lucide-react';

interface Briefing {
    id: number;
    status: string;
    script_content: string;
    created_at: string;
}

const Player: React.FC = () => {
    const [briefing, setBriefing] = useState<Briefing | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [briefingTime, setBriefingTime] = useState('07:00');

    useEffect(() => {
        fetchLatestBriefing();
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;

            const res = await fetch(`${API_BASE_URL}/settings/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setBriefingTime(data.briefing_time || '07:00');
            }
        } catch (error) {
            console.error('Failed to fetch settings', error);
        }
    };

    const fetchLatestBriefing = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) {
                setBriefing(null);
                return false;
            }

            const res = await fetch(`${API_BASE_URL}/briefings/latest?t=${Date.now()}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                // Optional: Check if it's actually new (by date) if we had previous data
                // For now just checking if we got ANY data
                setBriefing(data);
                return true;
            } else {
                // Keep old briefing if 404? Or clear? 
                // If 404, it means NO briefing exists.
                // setBriefing(null); // Don't clear immediately while polling or we flicker
                return false;
            }
        } catch (err) {
            console.error(err);
            return false;
        } finally {
            setLoading(false);
        }
    };

    const generateBriefing = async () => {
        setGenerating(true);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/briefings/generate`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Fehler beim Generieren');
            }

            alert("Briefing wird generiert! Dies dauert ca. 30 Sekunden...");

            // Start Polling
            let attempts = 0;
            const maxAttempts = 20; // 20 * 3s = 60s max

            const pollInterval = setInterval(async () => {
                attempts++;
                const success = await fetchLatestBriefing(); // Reuse existing fetch logic

                // If we found a briefing OR max attempts reached
                if (success || attempts >= maxAttempts) {
                    clearInterval(pollInterval);
                    setGenerating(false);
                    if (!success) {
                        alert("Zeitüberschreitung: Briefing wird noch verarbeitet. Bitte lade die Seite in Kürze neu.");
                    }
                }
            }, 3000);

        } catch (error) {
            console.error("Failed to generate", error);
            alert(`Fehler: ${(error as Error).message}`);
            setGenerating(false);
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center p-12">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center animate-pulse-slow mb-4">
                <Volume2 className="w-8 h-8 text-white" />
            </div>
            <p className="text-gray-400 animate-pulse">Lade Briefing...</p>
        </div>
    );

    if (!briefing) return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
            {/* Decorative Icon */}
            <div className="relative mb-6">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center border border-white/10">
                    <Clock className="w-10 h-10 text-purple-400" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg">
                    <Sparkles className="w-4 h-4 text-white" />
                </div>
            </div>

            <h3 className="text-xl font-bold text-white mb-2">
                Kein Briefing vorhanden
            </h3>
            <p className="text-gray-400 mb-6 max-w-xs">
                Dein nächstes Briefing wird um <strong className="text-purple-400">{briefingTime} Uhr</strong> generiert.
            </p>

            <button
                onClick={generateBriefing}
                disabled={generating}
                className="btn-primary flex items-center gap-2"
            >
                {generating ? (
                    <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        Generiere...
                    </>
                ) : (
                    <>
                        <Sparkles className="w-5 h-5" />
                        Jetzt generieren
                    </>
                )}
            </button>
        </div>
    );

    return (
        <div className="flex flex-col items-center space-y-6 w-full">
            {/* Header */}
            <div className="text-center">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/20 border border-green-500/30 text-green-400 text-xs mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    Briefing bereit
                </div>
                <h3 className="text-xl font-bold text-white">
                    {new Date(briefing.created_at).toLocaleDateString('de-DE', {
                        weekday: 'long',
                        day: 'numeric',
                        month: 'long'
                    })}
                </h3>
            </div>

            {/* Audio Player */}
            <div className="w-full p-4 rounded-2xl bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-white/10">
                <audio
                    controls
                    className="w-full"
                    src={`${API_BASE_URL}/briefings/${briefing.id}/audio`}
                    style={{ filter: 'invert(1)' }}
                />
            </div>

            {/* Script Preview */}
            <details className="w-full group">
                <summary className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-white transition-colors">
                    <Play className="w-4 h-4" />
                    Transkript anzeigen
                </summary>
                <div className="mt-3 p-4 rounded-xl bg-black/30 border border-white/5 text-sm text-gray-300 max-h-40 overflow-y-auto">
                    {briefing.script_content}
                </div>
            </details>

            {/* Regenerate Button */}
            <button
                onClick={generateBriefing}
                disabled={generating}
                className="text-xs text-gray-500 hover:text-purple-400 transition-colors flex items-center gap-1"
            >
                <RefreshCw className={`w-3 h-3 ${generating ? 'animate-spin' : ''}`} />
                Neu generieren
            </button>
        </div>
    );
};

export default Player;
