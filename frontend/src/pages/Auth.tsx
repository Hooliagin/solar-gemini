```javascript
import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { Loader2, Sparkles, Mail, ArrowRight } from 'lucide-react';

export default function AuthPage() {
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<'login' | 'signup' | 'forgot' | 'update'>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    React.useEffect(() => {
        // Check if we are on the update-password route
        if (window.location.pathname === '/update-password') {
            setMode('update');
        }
    }, []);

    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');

        try {
            if (mode === 'signup') {
                const { error } = await supabase.auth.signUp({
                    email,
                    password,
                });
                if (error) throw error;
                setMessage('Account created! Please check your email to verify.');
            } else if (mode === 'login') {
                const { error } = await supabase.auth.signInWithPassword({
                    email,
                    password,
                });
                if (error) throw error;
                // Session listener in AuthContext will handle redirect
            } else if (mode === 'forgot') {
                const { error } = await supabase.auth.resetPasswordForEmail(email, {
                    redirectTo: `${ window.location.origin }/update-password`,
                });
if (error) throw error;
setMessage('Check your email for the password reset link!');
            } else if (mode === 'update') {
    const { error } = await supabase.auth.updateUser({
        password: password
    });
    if (error) throw error;
    setMessage('Password updated successfully! Redirecting...');
    setTimeout(() => {
        window.location.href = '/';
    }, 1500);
}
        } catch (error: any) {
    setMessage(error.message);
} finally {
    setLoading(false);
}
    };

return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden">
        {/* Animated Background Orbs */}
        <div className="fixed inset-0 pointer-events-none">
            <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[128px] animate-pulse-slow" />
            <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-blue-500/20 rounded-full blur-[128px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
        </div>

        <div className="w-full max-w-md z-10 animate-fade-in-up">
            {/* Logo & Title */}
            <div className="flex flex-col items-center mb-10">
                <div className="p-4 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl mb-6 shadow-2xl shadow-purple-500/30 glow-purple animate-float">
                    <Sparkles className="w-10 h-10 text-white" />
                </div>
                <h1 className="text-4xl font-bold gradient-text mb-2">
                    Daily Manager
                </h1>
                <p className="text-gray-400 text-center text-lg">
                    Dein persönlicher KI-Morgenassistent
                </p>
            </div>

            {/* Auth Card */}
            <div className="glass-card p-8">
                {mode !== 'update' && (
                    <div className="flex gap-4 mb-6 border-b border-gray-700 pb-2">
                        <button
                            onClick={() => setMode('login')}
                            className={`flex-1 pb-2 text-center transition-colors ${mode === 'login' ? 'text-purple-400 border-b-2 border-purple-400' : 'text-gray-400 hover:text-white'}`}
                        >
                            Anmelden
                        </button>
                        <button
                            onClick={() => setMode('signup')}
                            className={`flex-1 pb-2 text-center transition-colors ${mode === 'signup' ? 'text-purple-400 border-b-2 border-purple-400' : 'text-gray-400 hover:text-white'}`}
                        >
                            Registrieren
                        </button>
                    </div>
                )}

                <h2 className="text-xl font-semibold text-white mb-6 text-center">
                    {mode === 'login' && 'Willkommen zurück'}
                    {mode === 'signup' && 'Konto erstellen'}
                    {mode === 'forgot' && 'Passwort zurücksetzen'}
                    {mode === 'update' && 'Neues Passwort vergeben'}
                </h2>

                <form onSubmit={handleAuth} className="space-y-4">
                    {mode !== 'update' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">
                                E-Mail Adresse
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                <input
                                    type="email"
                                    placeholder="du@beispiel.de"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="input-field w-full pl-12"
                                />
                            </div>
                        </div>
                    )}

                    {mode !== 'forgot' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">
                                {mode === 'update' ? 'Neues Passwort' : 'Passwort'}
                            </label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                minLength={6}
                                className="input-field w-full pl-4"
                            />
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn-primary w-full flex items-center justify-center gap-3 mt-6"
                    >
                        {loading ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <>
                                {mode === 'login' && 'Einloggen'}
                                {mode === 'signup' && 'Konto erstellen'}
                                {mode === 'forgot' && 'Reset-Link senden'}
                                {mode === 'update' && 'Passwort speichern'}
                                <ArrowRight className="w-5 h-5" />
                            </>
                        )}
                    </button>
                </form>

                {mode === 'login' && (
                    <div className="mt-4 text-center">
                        <button
                            onClick={() => setMode('forgot')}
                            className="text-sm text-gray-400 hover:text-white transition-colors"
                        >
                            Passwort vergessen?
                        </button>
                    </div>
                )}

                {mode === 'forgot' && (
                    <div className="mt-4 text-center">
                        <button
                            onClick={() => setMode('login')}
                            className="text-sm text-gray-400 hover:text-white transition-colors"
                        >
                            Zurück zum Login
                        </button>
                    </div>
                )}

                {message && (
                    <div className={`mt-6 p-4 rounded-xl text-center text-sm animate-fade-in ${message.includes('check') || message.includes('updated')
                            ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                            : 'bg-red-500/20 text-red-300 border border-red-500/30'
                        }`}>
                        {message}
                    </div>
                )}
            </div>
        </div>
    </div>
);
}
