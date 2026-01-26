import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export default function LoadingScreen() {
    return (
        <motion.div
            className="fixed top-0 left-0 w-screen h-screen z-50 flex items-center justify-center bg-[var(--cyber-bg)]"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
        >
            {/* Scanline overlay */}
            <div className="absolute inset-0 pointer-events-none opacity-30">
                <div className="h-full bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.3)_2px,rgba(0,0,0,0.3)_4px)]" />
            </div>

            {/* Content */}
            <div className="relative z-10 text-center">
                {/* Logo */}
                <motion.div
                    className="inline-block p-6 border-2 border-[var(--cyber-accent)] glow-neon mb-8"
                    style={{
                        clipPath: 'polygon(0 12px, 12px 0, calc(100% - 12px) 0, 100% 12px, 100% calc(100% - 12px), calc(100% - 12px) 100%, 12px 100%, 0 calc(100% - 12px))'
                    }}
                    animate={{
                        rotate: [0, 360],
                        scale: [1, 1.1, 1]
                    }}
                    transition={{
                        rotate: { duration: 3, repeat: Infinity, ease: "linear" },
                        scale: { duration: 2, repeat: Infinity, ease: "easeInOut" }
                    }}
                >
                    <Sparkles className="w-16 h-16 text-[var(--cyber-accent)]" />
                </motion.div>

                {/* Loading Text */}
                <motion.h2
                    className="text-2xl font-bold text-[var(--cyber-accent)] mb-2 tracking-widest font-[Orbitron]"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                >
                    INITIALIZING<span className="animate-blink">_</span>
                </motion.h2>

                <p className="text-sm text-[var(--cyber-text-muted)] font-mono mb-8">
                    &gt; LOADING_DAILY_MANAGER.exe
                </p>

                {/* Progress Bar */}
                <div className="w-full max-w-xs mx-auto px-4">
                    <div
                        className="h-2 bg-[var(--cyber-border)] relative overflow-hidden"
                        style={{
                            clipPath: 'polygon(0 2px, 2px 0, calc(100% - 2px) 0, 100% 2px, 100% calc(100% - 2px), calc(100% - 2px) 100%, 2px 100%, 0 calc(100% - 2px))'
                        }}
                    >
                        <motion.div
                            className="absolute inset-y-0 left-0 bg-[var(--cyber-accent)]"
                            style={{
                                boxShadow: '0 0 10px var(--cyber-accent), 0 0 20px var(--cyber-accent)'
                            }}
                            initial={{ width: '0%' }}
                            animate={{ width: '100%' }}
                            transition={{
                                duration: 2,
                                repeat: Infinity,
                                ease: "easeInOut"
                            }}
                        />
                    </div>

                    {/* Loading Percentage */}
                    <motion.p
                        className="text-xs text-[var(--cyber-accent)] font-mono mt-3 text-right"
                        animate={{ opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                    >
                        LOADING...
                    </motion.p>
                </div>

                {/* Glitch Text Effect */}
                <motion.div
                    className="mt-8 text-xs text-[var(--cyber-text-muted)] font-mono"
                    animate={{
                        x: [-2, 2, -2, 0],
                        opacity: [0.5, 1, 0.5]
                    }}
                    transition={{
                        duration: 0.3,
                        repeat: Infinity,
                        repeatDelay: 2
                    }}
                >
                    [ ESTABLISHING_CONNECTION... ]
                </motion.div>
            </div>

            {/* Background particles */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {[...Array(20)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-1 h-1 bg-[var(--cyber-accent)] rounded-full"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`
                        }}
                        animate={{
                            y: [0, -100],
                            opacity: [0, 1, 0]
                        }}
                        transition={{
                            duration: 2 + Math.random() * 2,
                            repeat: Infinity,
                            delay: Math.random() * 2
                        }}
                    />
                ))}
            </div>
        </motion.div>
    );
}
