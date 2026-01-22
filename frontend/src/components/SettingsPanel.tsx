import { useEffect, useState } from 'react';
import { Cloud, MapPin, Save, Settings as SettingsIcon, Volume2, Calendar, Link, Unlink, Newspaper } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

// Available OpenAI TTS voices
const VOICES = [
    { id: 'alloy', name: 'Alloy', description: 'Neutral, balanced' },
    { id: 'echo', name: 'Echo', description: 'Warm, conversational' },
    { id: 'fable', name: 'Fable', description: 'Expressive, storyteller' },
    { id: 'onyx', name: 'Onyx', description: 'Deep, authoritative' },
    { id: 'nova', name: 'Nova', description: 'Friendly, upbeat' },
    { id: 'shimmer', name: 'Shimmer', description: 'Clear, professional' },
];

// Predefined news categories
const NEWS_CATEGORIES = [
    { key: 'news_politics', name: 'Politik', icon: '🏛️', description: 'Deutsche & internationale Politik' },
    { key: 'news_local', name: 'Lokal', icon: '📍', description: 'News aus deiner Stadt' },
    { key: 'news_economy', name: 'Wirtschaft', icon: '📈', description: 'DAX, Märkte, Unternehmen' },
    { key: 'news_tech', name: 'Technologie', icon: '💻', description: 'Tech, KI, Startups' },
    { key: 'news_sports', name: 'Sport', icon: '⚽', description: 'Bundesliga, Wettkämpfe' },
];

export default function SettingsPanel() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [city, setCity] = useState('');
    const [weatherEnabled, setWeatherEnabled] = useState(true);
    const [voiceId, setVoiceId] = useState('alloy');
    const [calendarConnected, setCalendarConnected] = useState(false);
    // News category toggles
    const [newsCategories, setNewsCategories] = useState({
        news_politics: true,
        news_local: true,
        news_economy: false,
        news_tech: false,
        news_sports: false,
    });

    // Telegram linking state
    const [telegramConnected, setTelegramConnected] = useState(false);
    const [linkCode, setLinkCode] = useState<string | null>(null);

    useEffect(() => {
        fetchSettings();
        checkCalendarStatus();
        // Check URL for OAuth callback result
        const params = new URLSearchParams(window.location.search);
        if (params.get('calendar_connected') === 'true') {
            setCalendarConnected(true);
            window.history.replaceState({}, '', window.location.pathname);
        }
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
                setCity(data.weather_city);
                setWeatherEnabled(data.weather_enabled);
                setVoiceId(data.voice_id || 'alloy');
                setTelegramConnected(data.telegram_enabled || false);

                // Load news category settings
                setNewsCategories({
                    news_politics: data.news_politics ?? true,
                    news_local: data.news_local ?? true,
                    news_economy: data.news_economy ?? false,
                    news_tech: data.news_tech ?? false,
                    news_sports: data.news_sports ?? false,
                });
            }
        } catch (error) {
            console.error('Failed to fetch settings', error);
        } finally {
            setLoading(false);
        }
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

    // ... (rest of calendar/news functions unchanged) ...
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
            console.error('Failed to check calendar status', error);
        }
    };

    const connectCalendar = async () => {
        const session = (await supabase.auth.getSession()).data.session;
        if (session?.user?.id) {
            window.location.href = `${API_BASE_URL}/auth/google?user_id=${session.user.id}`;
        } else {
            console.error('No user session found');
        }
    };

    const disconnectCalendar = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) return;

            await fetch(`${API_BASE_URL}/auth/google/disconnect`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            });
            setCalendarConnected(false);
        } catch (error) {
            console.error('Failed to disconnect calendar', error);
        }
    };

    const toggleNewsCategory = (key: string) => {
        setNewsCategories(prev => ({
            ...prev,
            [key]: !prev[key as keyof typeof prev]
        }));
    };

    const saveSettings = async () => {
        setSaving(true);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            const res = await fetch(`${API_BASE_URL}/settings/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    weather_enabled: weatherEnabled,
                    weather_city: city,
                    voice_id: voiceId,
                    ...newsCategories
                })
            });
            if (res.ok) {
                // Settings saved
            }
        } catch (error) {
            console.error('Failed to save settings', error);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="glass-card rounded-2xl p-6 animate-pulse">
                <div className="h-6 bg-white/10 rounded w-1/3 mb-4"></div>
                <div className="h-10 bg-white/10 rounded w-full"></div>
            </div>
        );
    }

    return (
        <div className="glass-card rounded-2xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                <SettingsIcon className="w-24 h-24 text-white/5 -rotate-12" />
            </div>

            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400">
                    Settings
                </span>
            </h2>

            <div className="space-y-6">
                {/* Telegram Connection - NEW */}
                <div className="space-y-3 p-4 bg-blue-500/10 rounded-xl border border-blue-500/20">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400">
                                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .24z" /></svg>
                            </div>
                            <div>
                                <h3 className="text-white font-medium">Telegram Bot</h3>
                                <p className="text-xs text-gray-400">Erhalte dein Briefing direkt im Chat</p>
                            </div>
                        </div>
                        {telegramConnected ? (
                            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> Connected
                            </span>
                        ) : (
                            <span className="text-xs px-2 py-1 bg-white/10 text-gray-400 rounded-full">Not connected</span>
                        )}
                    </div>

                    {!telegramConnected && (
                        <div className="ml-11">
                            {!linkCode ? (
                                <button
                                    onClick={generateLinkCode}
                                    className="text-sm px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors flex items-center gap-2"
                                >
                                    <Link className="w-4 h-4" /> Code generieren
                                </button>
                            ) : (
                                <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                                    <p className="text-sm text-gray-300">Sende diesen Code an den Bot:</p>
                                    <div className="flex items-center gap-3">
                                        <code className="text-xl font-mono font-bold bg-black/30 px-4 py-2 rounded-lg tracking-wider text-blue-400 select-all">
                                            /start {linkCode}
                                        </code>
                                        <a
                                            href="https://t.me/DailyvoiceManagerbot"
                                            target="_blank"
                                            rel="noreferrer"
                                            className="text-xs text-blue-400 hover:text-blue-300 underline"
                                        >
                                            Bot öffnen @DailyvoiceManagerbot
                                        </a>
                                    </div>
                                    <p className="text-xs text-yellow-500/80">Code ist nur kurzzeitig gültig.</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Google Calendar */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Calendar className="w-5 h-5 text-green-400" />
                            <span className="text-gray-300">Google Calendar</span>
                        </div>
                        {calendarConnected ? (
                            <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">Connected</span>
                        ) : (
                            <span className="text-xs px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full">Not connected</span>
                        )}
                    </div>
                    <div className="ml-8">
                        {calendarConnected ? (
                            <button onClick={disconnectCalendar} className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-all text-sm">
                                <Unlink className="w-4 h-4" />
                                Disconnect
                            </button>
                        ) : (
                            <button onClick={connectCalendar} className="flex items-center gap-2 px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-all text-sm">
                                <Link className="w-4 h-4" />
                                Connect Calendar
                            </button>
                        )}
                    </div>
                </div>

                {/* Weather */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Cloud className="w-5 h-5 text-blue-400" />
                            <span className="text-gray-300">Weather in Briefing</span>
                        </div>
                        <button
                            onClick={() => setWeatherEnabled(!weatherEnabled)}
                            className={`relative w-12 h-6 rounded-full transition-colors ${weatherEnabled ? 'bg-blue-500' : 'bg-white/20'}`}
                        >
                            <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${weatherEnabled ? 'left-7' : 'left-1'}`} />
                        </button>
                    </div>
                    {weatherEnabled && (
                        <div className="flex items-center gap-2 ml-8">
                            <MapPin className="w-4 h-4 text-gray-500" />
                            <input type="text" value={city} onChange={(e) => setCity(e.target.value)} placeholder="City (e.g. Berlin)" className="input-field flex-1 text-sm" />
                        </div>
                    )}
                </div>

                {/* News Categories */}
                <div className="space-y-3">
                    <div className="flex items-center gap-3">
                        <Newspaper className="w-5 h-5 text-orange-400" />
                        <span className="text-gray-300">News Kategorien</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 ml-8">
                        {NEWS_CATEGORIES.map((cat) => {
                            const isSelected = newsCategories[cat.key as keyof typeof newsCategories];
                            return (
                                <button
                                    key={cat.key}
                                    onClick={() => toggleNewsCategory(cat.key)}
                                    className={`p-3 rounded-lg border-2 text-left transition-all relative ${isSelected
                                        ? 'border-orange-500 bg-orange-500/30 ring-2 ring-orange-500/50 shadow-lg shadow-orange-500/20'
                                        : 'border-white/10 hover:border-white/30 bg-white/5 opacity-60 hover:opacity-100'
                                        }`}
                                >
                                    {/* Checkmark badge */}
                                    {isSelected && (
                                        <div className="absolute -top-2 -right-2 w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center shadow-lg">
                                            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                            </svg>
                                        </div>
                                    )}
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">{cat.icon}</span>
                                        <span className={`text-sm font-medium ${isSelected ? 'text-orange-300' : 'text-gray-400'}`}>
                                            {cat.name}
                                        </span>
                                    </div>
                                    <div className={`text-xs mt-1 ${isSelected ? 'text-orange-200/70' : 'text-gray-500'}`}>
                                        {cat.description}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                    <p className="text-xs text-gray-500 ml-8">
                        💡 Lokale News verwenden deine Wetter-Stadt: <strong>{city || 'nicht gesetzt'}</strong>
                    </p>
                </div>

                {/* Voice Selection */}
                <div className="space-y-3">
                    <div className="flex items-center gap-3">
                        <Volume2 className="w-5 h-5 text-purple-400" />
                        <span className="text-gray-300">Briefing Voice</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 ml-8">
                        {VOICES.map((voice) => (
                            <button
                                key={voice.id}
                                onClick={() => setVoiceId(voice.id)}
                                className={`p-3 rounded-lg border-2 text-left transition-all relative ${voiceId === voice.id ? 'border-purple-500 bg-purple-500/30 ring-2 ring-purple-500/50' : 'border-white/10 hover:border-white/30 bg-white/5'}`}
                            >
                                {voiceId === voice.id && (
                                    <div className="absolute top-2 right-2 w-4 h-4 bg-purple-500 rounded-full flex items-center justify-center">
                                        <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                )}
                                <div className={`font-medium text-sm ${voiceId === voice.id ? 'text-purple-300' : 'text-gray-300'}`}>{voice.name}</div>
                                <div className="text-xs text-gray-500">{voice.description}</div>
                            </button>
                        ))}
                    </div>
                </div>

                <button onClick={saveSettings} disabled={saving} className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-xl font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2">
                    <Save className="w-4 h-4" />
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>
        </div>
    );
}
