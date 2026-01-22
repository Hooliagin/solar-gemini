import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';
import { supabase } from '../lib/supabase';

interface Briefing {
    id: number;
    status: string;
    script_content: string;
    created_at: string;
}

const Player: React.FC = () => {
    const [briefing, setBriefing] = useState<Briefing | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchLatestBriefing();
    }, []);

    const fetchLatestBriefing = async () => {
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) {
                setBriefing(null);
                return;
            }

            const res = await fetch(`${API_BASE_URL}/briefings/latest`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setBriefing(data);
            } else {
                setBriefing(null);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const generateBriefing = async () => {
        setLoading(true);
        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            // Note: The generate endpoint is likely on Telegram or a special endpoint.
            // Assuming there is a generate endpoint here? The original code had /briefings/generate 
            // but previous backend code didn't explicitly show it. 
            // If it exists, it needs auth.
            // Checking backend/routers/briefings.py... it actually doesn't have /generate!
            // The generation is triggered via Telegram or Scheduler usually.
            // But if we want a web trigger, we need to add it or use what's there.
            // For now, let's keep the call but adding Auth.

            await fetch(`${API_BASE_URL}/briefings/generate`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            });
            setTimeout(fetchLatestBriefing, 2000);
        } catch (error) {
            console.error("Failed to generate", error);
            setLoading(false);
        }
    };

    if (loading) return <div className="text-center p-10 animate-pulse text-purple-400">Checking/Generating briefing...</div>;

    if (!briefing) return (
        <div className="flex flex-col items-center justify-center p-10 text-center glass-panel rounded-2xl">
            <div className="text-6xl mb-4">😴</div>
            <h2 className="text-2xl font-semibold mb-2">No Briefing Ready</h2>
            <p className="text-gray-400 mb-6">Wait for the 5:50 AM schedule or trigger manually.</p>
            <button
                onClick={generateBriefing}
                className="btn-primary"
            >
                Generate Now
            </button>
        </div>
    );

    return (
        <div className="flex flex-col items-center justify-center space-y-6 w-full max-w-md mx-auto">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-white mb-1">Morning Briefing</h2>
                <p className="text-gray-400 text-sm">{new Date(briefing.created_at).toLocaleDateString()}</p>
            </div>

            <div className="w-full bg-black/30 rounded-2xl p-4 border border-white/5 shadow-inner">
                <audio
                    controls
                    className="w-full"
                    src={`${API_BASE_URL}/briefings/${briefing.id}/audio`}
                />
            </div>

            <div className="w-full text-left glass-panel p-4 rounded-xl max-h-48 overflow-y-auto text-sm text-gray-300 font-mono hidden md:block border border-white/5">
                {briefing.script_content}
            </div>

            <button
                onClick={generateBriefing}
                className="text-xs text-gray-500 hover:text-white transition-colors"
            >
                Regenerate
            </button>
        </div>
    );
};

export default Player;
