import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';
import { supabase } from '../lib/supabase';
import { Play, RefreshCw, Clock, Pause, ArrowRight } from 'lucide-react';

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
    const [showTranscript, setShowTranscript] = useState(false);
    const [briefingTime, setBriefingTime] = useState('07:00');
    const [error, setError] = useState<string | null>(null);

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
                setBriefing(data);
                return true;
            } else {
                if (res.status !== 404) {
                    setError(`Error: ${res.status} ${res.statusText}`);
                }
                return false;
            }
        } catch (err) {
            console.error(err);
            setError(`Network Error: ${(err as Error).message}`);
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
                throw new Error(data.detail || 'Generation failed');
            }

            // Start Polling
            let attempts = 0;
            const maxAttempts = 30; // 90s max

            const pollInterval = setInterval(async () => {
                attempts++;
                const success = await fetchLatestBriefing();

                if (success) {
                    clearInterval(pollInterval);
                    setGenerating(false);
                } else if (attempts >= maxAttempts) {
                    clearInterval(pollInterval);
                    setGenerating(false);
                    setError("Timeout: Briefing is taking longer than expected.");
                }
            }, 3000);

        } catch (error) {
            console.error("Failed to generate", error);
            alert(`Error: ${(error as Error).message}`);
            setGenerating(false);
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center py-12">
            <div className="w-8 h-8 border border-charcoal border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-xs uppercase tracking-widest text-charcoal">Synchronisiere...</p>
        </div>
    );

    if (!briefing) return (
        <div className="flex flex-col h-full justify-between">
            <div className="flex-1 flex flex-col justify-center">
                <div className="mb-6 opacity-40">
                    <Clock strokeWidth={1} className="w-8 h-8 text-charcoal" />
                </div>
                <h3 className="text-2xl font-serif mb-2 text-charcoal">
                    Kein Briefing verfügbar.
                </h3>
                <p className="text-warm-grey font-serif italic mb-6 text-sm">
                    Geplant für {briefingTime}.
                </p>

                {error && (
                    <div className="mb-4 text-xs text-red-500 border-l-2 border-red-500 pl-3">
                        {error}
                    </div>
                )}
            </div>

            <button
                onClick={generateBriefing}
                disabled={generating}
                className="w-full flex justify-between items-center py-6 border-t border-charcoal group hover:bg-charcoal hover:text-alabaster transition-colors duration-500"
            >
                <span className="text-sm font-medium uppercase tracking-widest">
                    {generating ? 'Erstelle...' : 'Tagebuch Eintrag jetzt generieren'}
                </span>
                <span className="transform group-hover:translate-x-2 transition-transform duration-500">
                    {generating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
                </span>
            </button>
        </div>
    );

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex justify-between items-end mb-8 border-b border-charcoal/10 pb-4">
                <div>
                    <span className="text-[10px] uppercase tracking-widest text-warm-grey block mb-1">Status</span>
                    <span className="flex items-center gap-2 text-xs font-medium">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-600 animate-pulse" />
                        Bereit
                    </span>
                </div>
                <div className="text-right">
                    <span className="text-[10px] uppercase tracking-widest text-warm-grey block mb-1">Datum</span>
                    <span className="font-serif">
                        {new Date(briefing.created_at).toLocaleDateString('de-DE', {
                            weekday: 'short',
                            day: 'numeric',
                            month: 'short'
                        })}
                    </span>
                </div>
            </div>

            {/* Audio Player */}
            <div className="mb-8">
                <AudioPlayerWithAuth
                    url={`${API_BASE_URL}/briefings/${briefing.id}/audio`}
                />
            </div>

            {/* Script Preview (Collapsible) */}
            <div className="flex-1 flex flex-col min-h-0 mb-6 transition-all duration-300">
                <button
                    onClick={() => setShowTranscript(!showTranscript)}
                    className="flex items-center gap-2 text-xs uppercase tracking-widest text-charcoal/60 hover:text-charcoal transition-colors mb-4 group"
                >
                    <ArrowRight className={`w-3 h-3 transition-transform duration-300 ${showTranscript ? 'rotate-90' : ''}`} />
                    {showTranscript ? 'Text verbergen' : 'Text anzeigen'}
                </button>

                <div className={`
                    overflow-y-auto pr-2 custom-scrollbar transition-all duration-500 ease-in-out
                    ${showTranscript ? 'opacity-100 max-h-[400px]' : 'opacity-0 max-h-0'}
                `}>
                    <p className="font-serif text-lg leading-relaxed text-charcoal/90 whitespace-pre-wrap">
                        {briefing.script_content || "Nur Audio."}
                    </p>
                </div>
            </div>

            {/* Regenerate Button */}
            <button
                onClick={generateBriefing}
                disabled={generating}
                className="text-sm font-medium uppercase tracking-widest text-charcoal hover:bg-charcoal hover:text-alabaster transition-all flex items-center justify-center gap-3 mt-auto py-6 border-t border-charcoal w-full"
            >
                <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
                Tagebuch Eintrag jetzt generieren
            </button>
        </div>
    );
};

export default Player;

const AudioPlayerWithAuth = ({ url }: { url: string }) => {
    const [audioSrc, setAudioSrc] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    // Custom controls state
    const [isPlaying, setIsPlaying] = useState(false);
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);
    const audioRef = React.useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        const fetchAudio = async () => {
            try {
                const token = (await supabase.auth.getSession()).data.session?.access_token;
                if (!token) return;

                const res = await fetch(url, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (!res.ok) throw new Error(`Status: ${res.status}`);

                const blob = await res.blob();
                const objectUrl = URL.createObjectURL(blob);
                setAudioSrc(objectUrl);
            } catch (err) {
                console.error("Audio load failed", err);
                setError("Failed to load audio");
            } finally {
                setLoading(false);
            }
        };

        fetchAudio();
        return () => { if (audioSrc) URL.revokeObjectURL(audioSrc); };
    }, [url]);

    const togglePlay = () => {
        if (!audioRef.current) return;
        if (isPlaying) {
            audioRef.current.pause();
        } else {
            audioRef.current.play();
        }
        setIsPlaying(!isPlaying);
    };

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            setCurrentTime(audioRef.current.currentTime);
        }
    };

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const handleEnded = () => {
        setIsPlaying(false);
        setCurrentTime(0);
    };

    const formatTime = (time: number) => {
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (loading) return <div className="text-[10px] uppercase tracking-widest animate-pulse">Loading Audio...</div>;
    if (error) return <div className="text-[10px] text-red-500 uppercase tracking-widest">{error}</div>;

    return (
        <div className="py-4">
            <audio
                ref={audioRef}
                src={audioSrc || undefined}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={handleEnded}
            />

            <div className="flex items-center gap-6">
                <button
                    onClick={togglePlay}
                    className="w-12 h-12 bg-charcoal text-alabaster flex items-center justify-center hover:scale-105 transition-transform duration-300"
                >
                    {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
                </button>

                <div className="flex-1">
                    <div className="h-px bg-charcoal/20 w-full mb-2 relative group cursor-pointer">
                        <div
                            className="absolute top-0 left-0 h-full bg-charcoal transition-all duration-100"
                            style={{ width: `${(currentTime / duration) * 100}%` }}
                        />
                        {/* Simple scrubber input could go here */}
                    </div>
                    <div className="flex justify-between text-[10px] font-mono text-warm-grey">
                        <span>{formatTime(currentTime)}</span>
                        <span>{formatTime(duration)}</span>
                    </div>
                </div>
            </div>
        </div>
    );
};
