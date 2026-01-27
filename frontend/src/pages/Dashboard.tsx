import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Settings, Play, Mic, Sun, Moon, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Player from '../components/Player';
import Recorder from '../components/Recorder';
import DiaryList from '../components/DiaryList';
import { API_BASE_URL } from '../config';

// Animation variants
const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: { staggerChildren: 0.1 }
    }
};

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
};

export default function Dashboard() {
    const { session } = useAuth();
    const navigate = useNavigate();
    const [userName, setUserName] = useState('');
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [setupComplete, setSetupComplete] = useState(true); // Default true until checked

    // Check Setup Status (Name, Voice, City)
    useEffect(() => {
        const checkSetup = async () => {
            if (!session?.access_token) return;
            try {
                const res = await fetch(`${API_BASE_URL}/settings/`, {
                    headers: { Authorization: `Bearer ${session.access_token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    setUserName(data.name || '');

                    // Logic: Is setup "Complete"?
                    // We consider it complete if they have a Name and a Voice selected.
                    // City is optional but good to have.
                    const isComplete = !!(data.name && data.voice_id);
                    setSetupComplete(isComplete);
                }
            } catch (e) {
                console.error(e);
            }
        };
        checkSetup();
    }, [session]);

    const getTimeOfDay = () => {
        const hour = new Date().getHours();
        if (hour < 12) return { greeting: "Guten Morgen", icon: Sun };
        if (hour < 18) return { greeting: "Guten Tag", icon: Sun };
        return { greeting: "Guten Abend", icon: Moon };
    };

    const { greeting, icon: TimeIcon } = getTimeOfDay();

    return (
        <div className="min-h-screen text-white pb-20">
            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
                <div className="absolute top-[-10%] left-[-10%] w-[600px] h-[600px] bg-[var(--cyber-accent)]/5 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-[var(--cyber-secondary)]/5 rounded-full blur-[120px]" />
            </div>

            <div className="max-w-xl mx-auto px-4 py-8 md:py-12">
                {/* Header */}
                <header className="flex justify-between items-center mb-10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 flex items-center justify-center shadow-lg">
                            <TimeIcon className="w-5 h-5 text-[var(--cyber-accent)]" />
                        </div>
                        <div>
                            <p className="text-xs text-gray-400 font-mono mb-0.5">{greeting.toUpperCase()}</p>
                            <h1 className="text-xl font-bold tracking-wide">{userName || 'User'}</h1>
                        </div>
                    </div>

                    <button
                        onClick={() => navigate('/settings')}
                        className="relative p-3 bg-white/5 hover:bg-white/10 rounded-full transition-all border border-white/5 group"
                    >
                        <Settings className="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
                        {!setupComplete && (
                            <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full animate-pulse border-2 border-black" />
                        )}
                    </button>
                </header>

                {/* Setup Widget (Conditional) */}
                <AnimatePresence>
                    {!setupComplete && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="mb-8 overflow-hidden"
                        >
                            <div
                                onClick={() => navigate('/settings')}
                                className="bg-gradient-to-r from-orange-500/10 to-red-500/10 border border-orange-500/20 rounded-2xl p-4 flex items-center gap-4 cursor-pointer hover:border-orange-500/40 transition-all"
                            >
                                <div className="p-3 bg-orange-500/20 rounded-full">
                                    <AlertCircle className="w-6 h-6 text-orange-400" />
                                </div>
                                <div className="flex-1">
                                    <h3 className="font-semibold text-orange-100">Setup abschließen</h3>
                                    <p className="text-sm text-orange-200/60">Bitte wähle deinen Namen & Stimme.</p>
                                </div>
                                <Play className="w-4 h-4 text-orange-400 opacity-50" />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <motion.main
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-6"
                >
                    {/* Primary Action: Briefing Player */}
                    <motion.div variants={itemVariants}>
                        <div className="flex items-center gap-2 mb-3 px-1">
                            <Play className="w-4 h-4 text-[var(--cyber-accent)]" />
                            <span className="text-sm font-medium text-gray-400 tracking-wider">DEIN BRIEFING</span>
                        </div>
                        <div className="glass-card p-6 bg-gradient-to-b from-white/5 to-transparent">
                            <Player />
                        </div>
                    </motion.div>

                    {/* Secondary Action: Recorder */}
                    <motion.div variants={itemVariants}>
                        <div className="flex items-center gap-2 mb-3 px-1">
                            <Mic className="w-4 h-4 text-[var(--cyber-secondary)]" />
                            <span className="text-sm font-medium text-gray-400 tracking-wider">TAGEBUCH</span>
                        </div>
                        <div className="glass-card p-6">
                            <Recorder onUploadComplete={() => setRefreshTrigger(p => p + 1)} />
                        </div>
                    </motion.div>

                    {/* Recent History */}
                    <motion.div variants={itemVariants} className="pt-6">
                        <div className="flex items-center justify-between mb-4 px-1">
                            <h3 className="text-sm font-medium text-gray-400 tracking-wider">VERLAUF</h3>
                        </div>
                        <div className="glass-card px-4 py-2 min-h-[200px]">
                            <DiaryList refreshTrigger={refreshTrigger} />
                        </div>
                    </motion.div>

                </motion.main>
            </div>
        </div>
    );
}
