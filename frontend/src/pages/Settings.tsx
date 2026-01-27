import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, LogOut } from 'lucide-react';
import SettingsPanel from '../components/SettingsPanel';
import InterestManager from '../components/InterestManager';
import { useAuth } from '../context/AuthContext';

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

export default function Settings() {
    const navigate = useNavigate();
    const { signOut } = useAuth();

    return (
        <div className="min-h-screen text-white pb-20">
            {/* Background */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[100px]" />
                <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[100px]" />
            </div>

            <div className="max-w-4xl mx-auto px-4 py-8">
                {/* Header */}
                <header className="flex items-center justify-between mb-8">
                    <button
                        onClick={() => navigate('/')}
                        className="p-2 hover:bg-white/10 rounded-full transition-colors flex items-center gap-2 text-gray-400 hover:text-white"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        <span className="text-sm font-medium">Zurück</span>
                    </button>

                    <h1 className="text-xl font-bold tracking-wider flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-[var(--cyber-accent)]" />
                        EINSTELLUNGEN
                    </h1>

                    <button
                        onClick={signOut}
                        className="p-2 hover:bg-red-500/10 text-gray-400 hover:text-red-400 rounded-full transition-colors"
                        title="Abmelden"
                    >
                        <LogOut className="w-5 h-5" />
                    </button>
                </header>

                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-8"
                >
                    <motion.section variants={itemVariants}>
                        <h2 className="text-lg font-semibold text-gray-300 mb-4 ml-1">Interessen & Themen</h2>
                        <InterestManager />
                    </motion.section>

                    <motion.section variants={itemVariants}>
                        <h2 className="text-lg font-semibold text-gray-300 mb-4 ml-1">System & Verbindungen</h2>
                        <SettingsPanel />
                    </motion.section>
                </motion.div>
            </div>
        </div>
    );
}
