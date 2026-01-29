import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, LogOut } from 'lucide-react';
import SettingsPanel from '../components/SettingsPanel';
import InterestManager from '../components/InterestManager';
import { useAuth } from '../context/AuthContext';

import HabitManager from '../components/HabitManager';

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
    const [isDirty, setIsDirty] = useState(false);

    const handleBack = () => {
        if (isDirty) {
            if (window.confirm("Sie haben ungespeicherte Änderungen. Möchten Sie wirklich verlassen?")) {
                navigate('/');
            }
        } else {
            navigate('/');
        }
    };

    const handleSignOut = () => {
        if (isDirty) {
            if (window.confirm("Sie haben ungespeicherte Änderungen. Möchten Sie wirklich verlassen?")) {
                signOut();
            }
        } else {
            signOut();
        }
    };

    return (
        <div className="min-h-screen text-charcoal pb-32 animate-fade-in">
            {/* Background Texture (Global is already applied, but we ensure no conflicts) */}

            <div className="max-w-[1000px] mx-auto px-8 md:px-16 py-12">
                {/* Header */}
                <header className="flex items-end justify-between mb-24 border-b border-charcoal/10 pb-8">
                    <button
                        onClick={handleBack}
                        className="group flex items-center gap-3 text-warm-grey hover:text-charcoal transition-colors duration-500"
                    >
                        <ArrowLeft strokeWidth={1} className="w-5 h-5 transform group-hover:-translate-x-1 transition-transform" />
                        <span className="text-xs uppercase tracking-[0.2em]">Zurück</span>
                    </button>

                    <h1 className="text-4xl md:text-5xl font-serif tracking-tight text-center absolute left-1/2 -translate-x-1/2">
                        Einstellungen
                    </h1>

                    <button
                        onClick={handleSignOut}
                        className="group flex items-center gap-2 text-warm-grey hover:text-charcoal transition-colors duration-500"
                        title="Abmelden"
                    >
                        <span className="hidden md:block text-xs uppercase tracking-[0.2em] opacity-0 group-hover:opacity-100 transition-opacity">Abmelden</span>
                        <LogOut strokeWidth={1} className="w-5 h-5" />
                    </button>
                </header>

                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="space-y-24"
                >
                    <motion.section variants={itemVariants}>
                        <div className="flex items-center gap-4 mb-12">
                            <span className="text-xs font-mono text-charcoal/40">01</span>
                            <h2 className="text-sm font-sans uppercase tracking-[0.2em] flex-1 border-b border-charcoal/10 pb-1">Interessen & Themen</h2>
                        </div>
                        <InterestManager />
                    </motion.section>

                    <motion.section variants={itemVariants}>
                        <div className="flex items-center gap-4 mb-12">
                            <span className="text-xs font-mono text-charcoal/40">02</span>
                            <h2 className="text-sm font-sans uppercase tracking-[0.2em] flex-1 border-b border-charcoal/10 pb-1">Tägliche Gewohnheiten & Ziele</h2>
                        </div>
                        <HabitManager />
                    </motion.section>

                    <motion.section variants={itemVariants}>
                        <div className="flex items-center gap-4 mb-12">
                            <span className="text-xs font-mono text-charcoal/40">03</span>
                            <h2 className="text-sm font-sans uppercase tracking-[0.2em] flex-1 border-b border-charcoal/10 pb-1">System & Verbindungen</h2>
                        </div>
                        <SettingsPanel onDirtyChange={setIsDirty} />
                    </motion.section>
                </motion.div>
            </div>
        </div>
    );
}
