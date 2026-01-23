import { useEffect, useState } from 'react';
import {
    Cloud, MapPin, Save, Volume2, Calendar, Link, Unlink,
    Clock, MessageCircle, CheckCircle, Globe, Zap, User
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

// Voice options with colors
const VOICES = [
    { id: 'alloy', name: 'Alloy', desc: 'Neutral', color: 'from-gray-400 to-gray-600', icon: '🎭' },
    { id: 'echo', name: 'Echo', desc: 'Warm', color: 'from-amber-400 to-orange-500', icon: '🌅' },
    { id: 'fable', name: 'Fable', desc: 'Storyteller', color: 'from-purple-400 to-pink-500', icon: '📖' },
    { id: 'onyx', name: 'Onyx', desc: 'Deep', color: 'from-slate-600 to-slate-800', icon: '🎸' },
    { id: 'nova', name: 'Nova', desc: 'Friendly', color: 'from-cyan-400 to-blue-500', icon: '✨' },
    { id: 'shimmer', name: 'Shimmer', desc: 'Clear', color: 'from-emerald-400 to-teal-500', icon: '💎' },
];

// News categories with colors
const NEWS_CATS = [
    { key: 'news_politics', name: 'Politik', icon: '🏛️', color: 'bg-red-500' },
    { key: 'news_local', name: 'Lokal', icon: '📍', color: 'bg-blue-500' },
    { key: 'news_economy', name: 'Wirtschaft', icon: '📈', color: 'bg-green-500' },
    { key: 'news_tech', name: 'Tech', icon: '💻', color: 'bg-purple-500' },
    { key: 'news_sports', name: 'Sport', icon: '⚽', color: 'bg-orange-500' },
];

export default function SettingsPanel() {
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

    useEffect(() => {
        fetchSettings();
        checkCalendarStatus();
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
                    ...newsCategories
                })
            });
            if (res.ok) {
                setSaved(true);
                setTimeout(() => setSaved(false), 2000);
            }
        } catch (error) {
            console.error('Failed to save settings', error);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="glass-card rounded-2xl p-8 animate-pulse">
                <div className="h-6 bg-white/10 rounded w-1/3 mb-6" />
                <div className="space-y-4">
                    <div className="h-16 bg-white/5 rounded-xl" />
                    <div className="h-16 bg-white/5 rounded-xl" />
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold gradient-text">Einstellungen</h2>
                <button
                    onClick={saveSettings}
                    disabled={saving}
                    className={`btn-primary flex items-center gap-2 ${saved ? 'bg-green-500' : ''}`}
                >
                    {saving ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : saved ? (
                        <CheckCircle className="w-5 h-5" />
                    ) : (
                        <Save className="w-5 h-5" />
                    )}
                    {saving ? 'Speichern...' : saved ? 'Gespeichert!' : 'Speichern'}
                </button>
            </div>

            {/* Connections Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Telegram Card */}
                <div className="glass-card p-5 rounded-2xl">
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                                <MessageCircle className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-white">Telegram</h3>
                                <p className="text-xs text-gray-400">Briefing im Chat</p>
                            </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${telegramConnected
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-white/10 text-gray-400'
                            }`}>
                            {telegramConnected ? '✓ Verbunden' : 'Nicht verbunden'}
                        </span>
                    </div>
                    {!telegramConnected && (
                        <div className="mt-4">
                            {!linkCode ? (
                                <button onClick={generateLinkCode} className="w-full py-2.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2">
                                    <Link className="w-4 h-4" />
                                    Code generieren
                                </button>
                            ) : (
                                <div className="p-3 bg-black/30 rounded-xl">
                                    <p className="text-xs text-gray-400 mb-2">Sende an @DailyvoiceManagerbot:</p>
                                    <code className="text-lg font-mono font-bold text-blue-400">/start {linkCode}</code>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Calendar Card */}
                <div className="glass-card p-5 rounded-2xl">
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/30">
                                <Calendar className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-white">Google Kalender</h3>
                                <p className="text-xs text-gray-400">Termine im Briefing</p>
                            </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${calendarConnected
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-white/10 text-gray-400'
                            }`}>
                            {calendarConnected ? '✓ Verbunden' : 'Nicht verbunden'}
                        </span>
                    </div>
                    <div className="mt-4">
                        {calendarConnected ? (
                            <button onClick={disconnectCalendar} className="w-full py-2.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2">
                                <Unlink className="w-4 h-4" />
                                Trennen
                            </button>
                        ) : (
                            <button onClick={connectCalendar} className="w-full py-2.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2">
                                <Link className="w-4 h-4" />
                                Verbinden
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Name Input */}
            <div className="glass-card p-5 rounded-2xl">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-400 to-rose-500 flex items-center justify-center">
                        <User className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h3 className="font-medium text-white">Dein Name</h3>
                        <p className="text-xs text-gray-500">Für persönliche Ansprache</p>
                    </div>
                </div>
                <input
                    type="text"
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                    placeholder="z.B. Max"
                    className="input-field w-full"
                />
            </div>

            {/* Location & Time */}
            <div className="glass-card p-5 rounded-2xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* City */}
                    <div>
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center">
                                <Globe className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h3 className="font-medium text-white">Standort</h3>
                                <p className="text-xs text-gray-500">Für Wetter & lokale News</p>
                            </div>
                        </div>
                        <div className="relative">
                            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                            <input
                                type="text"
                                value={city}
                                onChange={(e) => setCity(e.target.value)}
                                placeholder="z.B. Hamburg"
                                className="input-field w-full pl-10"
                            />
                        </div>
                    </div>

                    {/* Briefing Time */}
                    <div>
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                                <Clock className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h3 className="font-medium text-white">Briefing-Zeit</h3>
                                <p className="text-xs text-gray-500">Tägliche Zustellung</p>
                            </div>
                        </div>
                        <input
                            type="time"
                            value={briefingTime}
                            onChange={(e) => setBriefingTime(e.target.value)}
                            className="input-field w-full text-center text-lg font-mono"
                        />
                    </div>
                </div>

                {/* Weather Toggle */}
                <div className="mt-6 flex items-center justify-between p-4 bg-white/5 rounded-xl">
                    <div className="flex items-center gap-3">
                        <Cloud className="w-5 h-5 text-blue-400" />
                        <span className="text-gray-300">Wetter im Briefing</span>
                    </div>
                    <button
                        onClick={() => setWeatherEnabled(!weatherEnabled)}
                        className={`relative w-14 h-7 rounded-full transition-all duration-300 ${weatherEnabled ? 'bg-gradient-to-r from-blue-500 to-cyan-500' : 'bg-white/20'
                            }`}
                    >
                        <div className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow-lg transition-all duration-300 ${weatherEnabled ? 'left-8' : 'left-1'
                            }`} />
                    </button>
                </div>
            </div>

            {/* News Categories */}
            <div className="glass-card p-5 rounded-2xl">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center">
                        <Zap className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h3 className="font-medium text-white">News Kategorien</h3>
                        <p className="text-xs text-gray-500">Was interessiert dich?</p>
                    </div>
                </div>
                <div className="flex flex-wrap gap-2">
                    {NEWS_CATS.map((cat) => {
                        const isActive = newsCategories[cat.key as keyof typeof newsCategories];
                        return (
                            <button
                                key={cat.key}
                                onClick={() => setNewsCategories(prev => ({ ...prev, [cat.key]: !isActive }))}
                                className={`px-4 py-2.5 rounded-xl font-medium text-sm transition-all flex items-center gap-2 ${isActive
                                    ? `${cat.color} text-white shadow-lg`
                                    : 'bg-white/10 text-gray-400 hover:bg-white/20'
                                    }`}
                            >
                                <span className="text-lg">{cat.icon}</span>
                                {cat.name}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Voice Selection */}
            <div className="glass-card p-5 rounded-2xl">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center">
                        <Volume2 className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h3 className="font-medium text-white">Stimme wählen</h3>
                        <p className="text-xs text-gray-500">Für dein Audio-Briefing</p>
                    </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {VOICES.map((voice) => {
                        const isSelected = voiceId === voice.id;
                        return (
                            <button
                                key={voice.id}
                                onClick={() => setVoiceId(voice.id)}
                                className={`relative p-4 rounded-xl text-left transition-all ${isSelected
                                    ? `bg-gradient-to-br ${voice.color} shadow-lg scale-[1.02]`
                                    : 'bg-white/5 hover:bg-white/10 border border-white/10'
                                    }`}
                            >
                                {isSelected && (
                                    <div className="absolute top-2 right-2 w-5 h-5 bg-white rounded-full flex items-center justify-center">
                                        <CheckCircle className="w-4 h-4 text-gray-900" />
                                    </div>
                                )}
                                <span className="text-2xl mb-2 block">{voice.icon}</span>
                                <div className={`font-medium ${isSelected ? 'text-white' : 'text-gray-300'}`}>
                                    {voice.name}
                                </div>
                                <div className={`text-xs ${isSelected ? 'text-white/70' : 'text-gray-500'}`}>
                                    {voice.desc}
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
