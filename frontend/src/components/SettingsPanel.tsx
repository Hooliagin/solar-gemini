import { useEffect, useState } from 'react';
import { Cloud, MapPin, Save, Settings as SettingsIcon, Volume2, Calendar, Link, Unlink } from 'lucide-react';
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

export default function SettingsPanel() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [city, setCity] = useState('');
    const [weatherEnabled, setWeatherEnabled] = useState(true);
    const [voiceId, setVoiceId] = useState('alloy');
    const [calendarConnected, setCalendarConnected] = useState(false);

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
            const res = await fetch(`${API_BASE_URL}/settings/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setCity(data.weather_city);
                setWeatherEnabled(data.weather_enabled);
                setVoiceId(data.voice_id || 'alloy');
            }
        } catch (error) {
            console.error('Failed to fetch settings', error);
        } finally {
            setLoading(false);
        }
    };

    const checkCalendarStatus = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/auth/google/status`);
            if (res.ok) {
                const data = await res.json();
                setCalendarConnected(data.connected);
            }
        } catch (error) {
            console.error('Failed to check calendar status', error);
        }
    };

    const connectCalendar = () => {
        window.location.href = `${API_BASE_URL}/auth/google`;
    };

    const disconnectCalendar = async () => {
        try {
            await fetch(`${API_BASE_URL}/auth/google/disconnect`, { method: 'POST' });
            setCalendarConnected(false);
        } catch (error) {
            console.error('Failed to disconnect calendar', error);
        }
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
                    voice_id: voiceId
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
