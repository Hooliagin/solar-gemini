import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';

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
            const res = await fetch(`${API_BASE_URL}/briefings/latest`);
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

    if (loading) return <div className="text-center p-10">Checking for briefing...</div>;

    if (!briefing) return (
        <div className="flex flex-col items-center justify-center p-10 text-center">
            <div className="text-6xl mb-4">😴</div>
            <h2 className="text-2xl font-semibold">No Briefing Ready</h2>
            <p className="text-gray-400 mt-2">Wait for the 5:50 AM schedule or trigger manually.</p>
        </div>
    );

    return (
        <div className="flex flex-col items-center justify-center space-y-6 w-full max-w-md mx-auto p-6 bg-gray-800 rounded-2xl shadow-xl">
            <h2 className="text-2xl font-bold text-white">Morning Briefing</h2>
            <p className="text-gray-400 text-sm">{new Date(briefing.created_at).toLocaleDateString()}</p>

            <div className="w-full bg-black/30 rounded-lg p-4">
                <audio
                    controls
                    className="w-full"
                    src={`${API_BASE_URL}/briefings/${briefing.id}/audio`}
                />
            </div>

            <div className="w-full text-left bg-gray-900/50 p-4 rounded-lg max-h-48 overflow-y-auto text-sm text-gray-300 font-mono hidden md:block">
                {briefing.script_content}
            </div>
        </div>
    );
};

export default Player;
