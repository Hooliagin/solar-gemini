import { useEffect, useState } from 'react';
import {
    MapPin, Save, Volume2, Calendar,
    MessageCircle, CheckCircle, Globe, Zap, User, Clock
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

// Voice options mapped to Gemini Personalities
const VOICES = [
    { id: 'alloy', name: 'Zephyr', color: 'bg-charcoal', icon: '🍃' },
    { id: 'echo', name: 'Fenrir', color: 'bg-gold', icon: '🔥' },
    { id: 'fable', name: 'Puck', color: 'bg-charcoal', icon: '📖' },
    { id: 'onyx', name: 'Kore', color: 'bg-gold', icon: '⚓' },
    { id: 'nova', name: 'Leda', color: 'bg-charcoal', icon: '✨' },
    { id: 'shimmer', name: 'Aoede', color: 'bg-gold', icon: '🌊' },
];

// News categories with minimal logic
const NEWS_CATS = [
    { key: 'news_politics', name: 'Politics', icon: '🏛️' },
    { key: 'news_local', name: 'Local', icon: '📍' },
    { key: 'news_economy', name: 'Economy', icon: '📈' },
    { key: 'news_tech', name: 'Tech', icon: '💻' },
    { key: 'news_sports', name: 'Sports', icon: '⚽' },
];

interface SettingsPanelProps {
    onDirtyChange?: (isDirty: boolean) => void;
}

export default function SettingsPanel({ onDirtyChange }: SettingsPanelProps) {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [userName, setUserName] = useState('');
    const [city, setCity] = useState('');
    const [weatherEnabled, setWeatherEnabled] = useState(true);
    const [voiceId, setVoiceId] = useState('alloy');
    const [briefingTime, setBriefingTime] = useState('07:00');
    const [calendarConnected, setCalendarConnected] = useState(false);
    const [telegramConnected, setTelegramConnected] = useState(false);
    const [linkCode, setLinkCode] = useState<string | null>(null);
    const [newsCategories, setNewsCategories] = useState({
        news_politics: true,
        news_local: true,
        news_economy: false,
        news_tech: false,
        news_sports: false,
    });
    const [reflectionTime, setReflectionTime] = useState('19:00');
    const [reflectionReminderEnabled, setReflectionReminderEnabled] = useState(true);

    // Dirty Checking State
    const [initialSettings, setInitialSettings] = useState<any>(null);

    // Calculate current state object for comparison
    const currentSettings = {
        name: userName,
        weather_enabled: weatherEnabled,
        weather_city: city,
        voice_id: voiceId,
        briefing_time: briefingTime,
        telegram_enabled: telegramConnected,
        ...newsCategories,
        reflection_time: reflectionTime,
        reflection_reminder_enabled: reflectionReminderEnabled
    };

    // Check for changes
    useEffect(() => {
        if (!initialSettings || loading) return;

        const isDirty = JSON.stringify(currentSettings) !== JSON.stringify(initialSettings);
        if (onDirtyChange) onDirtyChange(isDirty);

        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (isDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        };
        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);

    }, [currentSettings, initialSettings, loading, onDirtyChange]);

    // Audio Playback State
    const [playingVoice, setPlayingVoice] = useState<string | null>(null);
    const [audioLoading, setAudioLoading] = useState<string | null>(null);
    const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);

    useEffect(() => {
        fetchSettings();
        checkCalendarStatus();
        const params = new URLSearchParams(window.location.search);
        if (params.get('calendar_connected') === 'true') {
            setCalendarConnected(true);
            window.history.replaceState({}, '', window.location.pathname);
        }
    }, []);

    // Poll for changes when link code is active
    useEffect(() => {
        if (!linkCode || telegramConnected) return;

        const interval = setInterval(() => {
            fetchSettings();
        }, 3000);

        return () => clearInterval(interval);
    }, [linkCode, telegramConnected]);

    const fetchSettings = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;
            const res = await fetch(`${API_BASE_URL}/settings/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setUserName(data.name || '');
                setCity(data.weather_city || '');
                setWeatherEnabled(data.weather_enabled ?? true);
                setVoiceId(data.voice_id || 'alloy');
                setBriefingTime(data.briefing_time || '07:00');
                setTelegramConnected(data.telegram_enabled || false);
                setNewsCategories({
                    news_politics: data.news_politics ?? true,
                    news_local: data.news_local ?? true,
                    news_economy: data.news_economy ?? false,
                    news_tech: data.news_tech ?? false,
                    news_sports: data.news_sports ?? false,
                });
                setReflectionTime(data.reflection_time || '19:00');
                setReflectionReminderEnabled(data.reflection_reminder_enabled ?? true);

                setInitialSettings({
                    name: data.name || '',
                    weather_enabled: data.weather_enabled ?? true,
                    weather_city: data.weather_city || '',
                    voice_id: data.voice_id || 'alloy',
                    briefing_time: data.briefing_time || '07:00',
                    telegram_enabled: data.telegram_enabled || false,
                    news_politics: data.news_politics ?? true,
                    news_local: data.news_local ?? true,
                    news_economy: data.news_economy ?? false,
                    news_tech: data.news_tech ?? false,
                    news_sports: data.news_sports ?? false,
                    reflection_time: data.reflection_time || '19:00',
                    reflection_reminder_enabled: data.reflection_reminder_enabled ?? true
                });
            }
        } catch (error) {
            console.error('Failed to fetch settings', error);
        } finally {
            setLoading(false);
        }
    };

    const checkCalendarStatus = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;
            const res = await fetch(`${API_BASE_URL}/auth/google/status`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setCalendarConnected(data.connected);
            }
        } catch (error) {
            console.error('Failed to check calendar', error);
        }
    };

    const connectCalendar = async () => {
        const session = (await supabase.auth.getSession()).data.session;
        if (session?.user?.id) {
            window.location.href = `${API_BASE_URL}/auth/google?user_id=${session.user.id}`;
        }
    };

    const disconnectCalendar = async () => {
        const token = (await supabase.auth.getSession()).data.session?.access_token;
        if (!token) return;
        await fetch(`${API_BASE_URL}/auth/google/disconnect`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` }
        });
        setCalendarConnected(false);
    };

    const generateLinkCode = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;
            const res = await fetch(`${API_BASE_URL}/settings/telegram/link-code`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setLinkCode(data.code);
            }
        } catch (error) {
            console.error('Failed to generate link code', error);
        }
    };

    const disconnectTelegram = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;

            const res = await fetch(`${API_BASE_URL}/settings/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    telegram_enabled: false,
                    telegram_chat_id: null
                })
            });

            if (res.ok) {
                setTelegramConnected(false);
                setLinkCode(null);
            }
        } catch (error) {
            console.error('Failed to disconnect Telegram', error);
            alert("Error disconnecting.");
        }
    };

    const saveSettings = async () => {
        setSaving(true);
        setSaved(false);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/settings/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    name: userName,
                    weather_enabled: weatherEnabled,
                    weather_city: city,
                    voice_id: voiceId,
                    briefing_time: briefingTime,
                    reflection_time: reflectionTime,
                    reflection_reminder_enabled: reflectionReminderEnabled,
                    ...newsCategories
                })
            });
            if (res.ok) {
                setSaved(true);
                setInitialSettings(currentSettings);
                setTimeout(() => setSaved(false), 2000);
            }
        } catch (error) {
            console.error('Failed to save settings', error);
        } finally {
            setSaving(false);
        }
    };

    const playPreview = async (voiceId: string) => {
        if (currentAudio) {
            currentAudio.pause();
            setCurrentAudio(null);
            setPlayingVoice(null);
            if (playingVoice === voiceId) return;
        }

        try {
            setAudioLoading(voiceId);
            const timestamp = new Date().getTime();
            const url = `${API_BASE_URL}/audio/preview/${voiceId}?t=${timestamp}`;
            const audio = new Audio(url);

            audio.addEventListener('canplaythrough', () => {
                setAudioLoading(null);
                setPlayingVoice(voiceId);
                audio.play().catch(e => {
                    console.error("Play error:", e);
                    setPlayingVoice(null);
                });
            });

            audio.addEventListener('ended', () => {
                setPlayingVoice(null);
                setCurrentAudio(null);
            });

            audio.addEventListener('error', (e) => {
                console.error("Audio Load Error:", e);
                setAudioLoading(null);
                setPlayingVoice(null);
                alert("Error loading preview.");
            });

            setCurrentAudio(audio);
            audio.load();

        } catch (err) {
            console.error("Audio init failed:", err);
            setAudioLoading(null);
        }
    };

    return (
        <div className={`space-y-16 ${loading ? 'opacity-70' : ''}`}>
            {/* Header Actions */}
            <div className="flex justify-end sticky top-8 z-30 pointer-events-none">
                <button
                    onClick={saveSettings}
                    disabled={saving || loading}
                    className={`pointer-events-auto btn-luxury-primary group transition-all ${saved ? 'bg-green-600 border-green-600' : ''}`}
                >
                    <div className="btn-luxury-primary-inner" />
                    <span className="flex items-center gap-3">
                        {saving ? (
                            <div className="w-3 h-3 border-2 border-alabaster border-t-transparent rounded-full animate-spin" />
                        ) : saved ? (
                            <CheckCircle className="w-4 h-4" />
                        ) : (
                            <Save className="w-4 h-4" />
                        )}
                        {saving ? 'SAVING...' : saved ? 'SAVED' : 'SAVE CHANGES'}
                    </span>
                </button>
            </div>

            {/* Connections */}
            <div className="grid grid-cols-1 gap-12">
                {/* Telegram */}
                <div className="card-luxury">
                    <div className="flex items-start justify-between mb-8">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <MessageCircle strokeWidth={1.5} className="w-5 h-5 text-charcoal" />
                                <h3 className="text-xl font-serif">Telegram Intelligence</h3>
                            </div>
                            <p className="text-warm-grey text-sm font-serif italic">Receive your daily briefing via chat.</p>
                        </div>
                        <span className={`text-xs tracking-widest uppercase py-1 px-2 border ${telegramConnected ? 'border-charcoal text-charcoal' : 'border-charcoal/20 text-charcoal/40'}`}>
                            {telegramConnected ? 'CONNECTED' : 'OFFLINE'}
                        </span>
                    </div>

                    {telegramConnected ? (
                        <button onClick={disconnectTelegram} className="text-xs uppercase tracking-widest text-red-500 hover:text-red-600 border-b border-red-200 pb-0.5">
                            Disconnect
                        </button>
                    ) : (
                        <div>
                            {!linkCode ? (
                                <button onClick={generateLinkCode} className="btn-luxury-outline w-full md:w-auto">
                                    Generate Connection Code
                                </button>
                            ) : (
                                <div className="space-y-4">
                                    <div className="p-4 bg-alabaster border border-charcoal/10 flex flex-col items-center">
                                        <span className="text-3xl font-serif tracking-widest mb-2">{linkCode}</span>
                                        <span className="text-xs uppercase text-warm-grey">Active Code</span>
                                    </div>
                                    <a
                                        href={`https://t.me/DailyvoiceManagerbot?start=${linkCode}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn-luxury-primary w-full md:w-auto inline-flex"
                                    >
                                        <div className="btn-luxury-primary-inner" />
                                        <span>Open Telegram</span>
                                    </a>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Calendar */}
                <div className="card-luxury">
                    <div className="flex items-start justify-between mb-8">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <Calendar strokeWidth={1.5} className="w-5 h-5 text-charcoal" />
                                <h3 className="text-xl font-serif">Google Calendar</h3>
                            </div>
                            <p className="text-warm-grey text-sm font-serif italic">Sync schedule for intelligent planning.</p>
                        </div>
                        <span className={`text-xs tracking-widest uppercase py-1 px-2 border ${calendarConnected ? 'border-charcoal text-charcoal' : 'border-charcoal/20 text-charcoal/40'}`}>
                            {calendarConnected ? 'CONNECTED' : 'OFFLINE'}
                        </span>
                    </div>
                    <div>
                        {calendarConnected ? (
                            <button onClick={disconnectCalendar} className="text-xs uppercase tracking-widest text-red-500 hover:text-red-600 border-b border-red-200 pb-0.5">
                                Disconnect
                            </button>
                        ) : (
                            <button onClick={connectCalendar} className="btn-luxury-outline w-full md:w-auto">
                                Connect Account
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                {/* Profile */}
                <div className="card-luxury">
                    <div className="flex items-center gap-3 mb-8 opacity-60">
                        <User strokeWidth={1} className="w-5 h-5" />
                        <span className="text-xs uppercase tracking-widest">Profile Identity</span>
                    </div>

                    <div className="space-y-8">
                        <div>
                            <label className="block text-xs uppercase tracking-widest text-warm-grey mb-2">Display Name</label>
                            <input
                                type="text"
                                value={userName}
                                onChange={(e) => setUserName(e.target.value)}
                                placeholder="E.g. Alexander"
                                className="input-luxury text-xl font-serif"
                            />
                        </div>
                        <div>
                            <label className="block text-xs uppercase tracking-widest text-warm-grey mb-2">Primary Location</label>
                            <div className="relative">
                                <input
                                    type="text"
                                    value={city}
                                    onChange={(e) => setCity(e.target.value)}
                                    placeholder="E.g. Vienna"
                                    className="input-luxury text-xl font-serif"
                                />
                                <MapPin strokeWidth={1} className="absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 text-charcoal/30" />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Timing */}
                <div className="card-luxury">
                    <div className="flex items-center gap-3 mb-8 opacity-60">
                        <Clock strokeWidth={1} className="w-5 h-5" />
                        <span className="text-xs uppercase tracking-widest">Routine Timing</span>
                    </div>

                    <div className="space-y-8">
                        <div>
                            <label className="block text-xs uppercase tracking-widest text-warm-grey mb-2">Morning Briefing</label>
                            <input
                                type="time"
                                value={briefingTime}
                                onChange={(e) => setBriefingTime(e.target.value)}
                                className="input-luxury text-3xl font-serif"
                            />
                        </div>

                        <div>
                            <div className="flex justify-between items-center mb-4">
                                <label className="block text-xs uppercase tracking-widest text-warm-grey">Evening Reflection</label>
                                <button
                                    onClick={() => setReflectionReminderEnabled(!reflectionReminderEnabled)}
                                    className={`w-8 h-4 border transition-colors ${reflectionReminderEnabled ? 'bg-charcoal border-charcoal' : 'border-charcoal/30'}`}
                                >
                                    <div className={`w-2 h-2 bg-alabaster mx-1 transition-transform ${reflectionReminderEnabled ? 'translate-x-full' : ''}`} />
                                </button>
                            </div>

                            {reflectionReminderEnabled && (
                                <input
                                    type="time"
                                    value={reflectionTime}
                                    onChange={(e) => setReflectionTime(e.target.value)}
                                    className="input-luxury text-3xl font-serif"
                                />
                            )}
                        </div>

                        <div className="pt-4 flex items-center justify-between">
                            <span className="font-serif">Include Weather Report</span>
                            <button
                                onClick={() => setWeatherEnabled(!weatherEnabled)}
                                className={`w-8 h-4 border transition-colors ${weatherEnabled ? 'bg-charcoal border-charcoal' : 'border-charcoal/30'}`}
                            >
                                <div className={`w-2 h-2 bg-alabaster mx-1 transition-transform ${weatherEnabled ? 'translate-x-full' : ''}`} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* News Categories */}
            <div className="card-luxury">
                <div className="flex items-center gap-3 mb-8 opacity-60">
                    <Globe strokeWidth={1} className="w-5 h-5" />
                    <span className="text-xs uppercase tracking-widest">Intelligence Sources</span>
                </div>

                <div className="flex flex-wrap gap-4">
                    {NEWS_CATS.map((cat) => {
                        const isActive = newsCategories[cat.key as keyof typeof newsCategories];
                        return (
                            <button
                                key={cat.key}
                                onClick={() => setNewsCategories(prev => ({ ...prev, [cat.key]: !isActive }))}
                                className={`px-6 py-4 border transition-all duration-300 ${isActive
                                    ? 'bg-charcoal text-alabaster border-charcoal shadow-lg transform -translate-y-1'
                                    : 'bg-transparent text-charcoal border-charcoal/20 hover:border-charcoal'
                                    }`}
                            >
                                <span className="block text-xs uppercase tracking-widest mb-1 opacity-60">{cat.icon}</span>
                                <span className="font-serif text-lg">{cat.name}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Voice Selection */}
            <div className="card-luxury">
                <div className="flex items-center gap-3 mb-8 opacity-60">
                    <Volume2 strokeWidth={1} className="w-5 h-5" />
                    <span className="text-xs uppercase tracking-widest">Assistant Voice</span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-6 gap-0 border border-charcoal/20">
                    {VOICES.map((voice, idx) => {
                        const isSelected = voiceId === voice.id;
                        const isPlaying = playingVoice === voice.id;
                        const isLoading = audioLoading === voice.id;

                        // Calculate grid borders manually for a clean look
                        const borderClasses = `
                             p-6 relative transition-all duration-300 hover:bg-charcoal/5
                             ${idx !== VOICES.length - 1 ? 'md:border-r border-charcoal/20' : ''} 
                             ${idx < VOICES.length - 2 ? 'border-b md:border-b-0 border-charcoal/20' : ''}
                        `;

                        return (
                            <button
                                key={voice.id}
                                onClick={() => setVoiceId(voice.id)}
                                className={`${borderClasses} ${isSelected ? 'bg-charcoal text-alabaster' : 'text-charcoal'}`}
                            >
                                <div className="flex flex-col items-center gap-4">
                                    <span className="text-2xl">{voice.icon}</span>
                                    <span className="font-serif tracking-wide">{voice.name}</span>

                                    <div
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            playPreview(voice.id);
                                        }}
                                        className={`mt-2 p-2 rounded-full border ${isSelected ? 'border-alabaster hover:bg-alabaster hover:text-charcoal' : 'border-charcoal hover:bg-charcoal hover:text-alabaster'} transition-colors`}
                                    >
                                        {isLoading ? (
                                            <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                                        ) : isPlaying ? (
                                            <div className="w-3 h-3 bg-current" />
                                        ) : (
                                            <Volume2 className="w-3 h-3" />
                                        )}
                                    </div>
                                </div>
                                {isSelected && (
                                    <div className="absolute top-2 right-2 w-2 h-2 bg-gold rounded-full" />
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Debug Section */}
            <div className="card-luxury opacity-40 hover:opacity-100 transition-opacity">
                <div className="flex items-center gap-3 mb-4">
                    <Zap strokeWidth={1} className="w-4 h-4" />
                    <h3 className="text-xs uppercase tracking-widest">System Diagnostics</h3>
                </div>
                <DebugInfo />
            </div>
        </div>
    );
}

function DebugInfo() {
    const [info, setInfo] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const checkHealth = async () => {
        setLoading(true);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;
            const res = await fetch(`${API_BASE_URL}/debug/me`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setInfo(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-3">
            {!info ? (
                <button
                    onClick={checkHealth}
                    disabled={loading}
                    className="text-xs font-mono text-charcoal underline hover:text-gold"
                >
                    {loading ? "Scanning..." : "Run Diagnostics"}
                </button>
            ) : (
                <div className="text-[10px] font-mono p-4 border border-charcoal/20 bg-alabaster">
                    <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                        <span className="text-warm-grey">USER ID</span>
                        <span>{info.my_user_id}</span>

                        <span className="text-warm-grey">TELEGRAM</span>
                        <span className={info.telegram_connected ? "text-green-600" : "text-red-500"}>{String(info.telegram_connected)}</span>

                        <span className="text-warm-grey">BRIEFINGS</span>
                        <span>{info.total_briefings}</span>
                    </div>

                    <button
                        onClick={() => setInfo(null)}
                        className="mt-4 text-xs underline"
                    >
                        Close Report
                    </button>
                </div>
            )}
        </div>
    );
}
