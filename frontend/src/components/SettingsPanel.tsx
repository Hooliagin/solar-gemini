import { useEffect, useState } from 'react';
import { Cloud, MapPin, Save, Settings as SettingsIcon } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../config';

export default function SettingsPanel() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [city, setCity] = useState('');
    const [weatherEnabled, setWeatherEnabled] = useState(true);

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
                    weather_city: city
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

            {/* Weather Section */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Cloud className="w-5 h-5 text-blue-400" />
                        <span className="text-gray-300">Weather in Briefing</span>
                    </div>
                    <button
                        onClick={() => setWeatherEnabled(!weatherEnabled)}
                        className={`relative w-12 h-6 rounded-full transition-colors ${weatherEnabled ? 'bg-blue-500' : 'bg-white/20'
                            }`}
                    >
                        <div
                            className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${weatherEnabled ? 'left-7' : 'left-1'
                                }`}
                        />
                    </button>
                </div>

                {weatherEnabled && (
                    <div className="flex items-center gap-2">
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

                <button
                    onClick={saveSettings}
                    disabled={saving}
                    className="w-full mt-4 py-2.5 px-4 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-xl font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    <Save className="w-4 h-4" />
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>
        </div>
    );
}
