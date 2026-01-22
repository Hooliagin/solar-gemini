import { useEffect, useState } from 'react';
import { Cloud, MapPin, Save, Settings as SettingsIcon, Volume2 } from 'lucide-react';
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

    useEffect(() => {
        fetchSettings();
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
                // Settings saved successfully
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
                {/* Weather Section */}
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
                            <div
                                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${weatherEnabled ? 'left-7' : 'left-1'}`}
                            />
                        </button>
                    </div>

                    {weatherEnabled && (
                        <div className="flex items-center gap-2 ml-8">
                            <MapPin className="w-4 h-4 text-gray-500" />
                            <input
                                type="text"
                                value={city}
                                onChange={(e) => setCity(e.target.value)}
                                placeholder="City (e.g. Berlin)"
                                className="input-field flex-1 text-sm"
                            />
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
                                className={`p-3 rounded-lg border text-left transition-all ${voiceId === voice.id
                                        ? 'border-purple-500 bg-purple-500/20'
                                        : 'border-white/10 hover:border-white/30 bg-white/5'
                                    }`}
                            >
                                <div className="font-medium text-sm">{voice.name}</div>
                                <div className="text-xs text-gray-500">{voice.description}</div>
                            </button>
                        ))}
                    </div>
                </div>

                <button
                    onClick={saveSettings}
                    disabled={saving}
                    className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-xl font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    <Save className="w-4 h-4" />
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>
        </div>
    );
}
