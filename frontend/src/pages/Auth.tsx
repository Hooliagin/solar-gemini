import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { Loader2, ArrowRight } from 'lucide-react';

export default function AuthPage() {
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<'login' | 'signup' | 'forgot' | 'update'>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    React.useEffect(() => {
        if (window.location.pathname === '/update-password') {
            setMode('update');
        }
    }, []);

    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');

        try {
            if (mode === 'login') {
                const { error } = await supabase.auth.signInWithPassword({
                    email,
                    password,
                });
                if (error) throw error;
                window.location.href = '/';
            } else if (mode === 'signup') {
                const { error } = await supabase.auth.signUp({
                    email,
                    password,
                });
                if (error) throw error;
                setMessage('Account created! Please check your email to verify.');
            } else if (mode === 'forgot') {
                const { error } = await supabase.auth.resetPasswordForEmail(email, {
                    redirectTo: `${window.location.origin}/update-password`,
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
        <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-alabaster">

            <div className="w-full max-w-md z-10">
                {/* Logo & Title */}
                <div className="flex flex-col items-center mb-16">
                    <h1 className="text-5xl font-serif text-charcoal mb-4 tracking-tight">
                        Daily Manager.
                    </h1>
                    <p className="text-warm-grey font-serif italic text-lg">
                        Your personal intelligence suite.
                    </p>
                </div>

                {/* Auth Card */}
                <div className="card-luxury p-8 md:p-12">
                    {mode !== 'update' && (
                        <div className="flex mb-12 border-b border-charcoal/10">
                            <button
                                onClick={() => setMode('login')}
                                className={`flex-1 pb-4 text-xs uppercase tracking-widest transition-all ${mode === 'login' ? 'text-charcoal border-b border-charcoal' : 'text-warm-grey hover:text-charcoal/70'}`}
                            >
                                Login
                            </button>
                            <button
                                onClick={() => setMode('signup')}
                                className={`flex-1 pb-4 text-xs uppercase tracking-widest transition-all ${mode === 'signup' ? 'text-charcoal border-b border-charcoal' : 'text-warm-grey hover:text-charcoal/70'}`}
                            >
                                Join
                            </button>
                        </div>
                    )}

                    <form onSubmit={handleAuth} className="space-y-8">
                        {mode !== 'update' && (
                            <div>
                                <label className="block text-xs uppercase tracking-widest text-warm-grey mb-3">
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="input-luxury"
                                />
                            </div>
                        )}

                        {mode !== 'forgot' && (
                            <div>
                                <label className="block text-xs uppercase tracking-widest text-warm-grey mb-3">
                                    {mode === 'update' ? 'New Password' : 'Password'}
                                </label>
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    minLength={6}
                                    className="input-luxury"
                                />
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-luxury-primary group w-full flex items-center justify-center gap-4 mt-8"
                        >
                            {loading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <>
                                    <span className="relative z-10">
                                        {mode === 'login' && 'Enter Suite'}
                                        {mode === 'signup' && 'Create Account'}
                                        {mode === 'forgot' && 'Send Reset Link'}
                                        {mode === 'update' && 'Update Password'}
                                    </span>
                                    <ArrowRight className="w-4 h-4 relative z-10" />
                                </>
                            )}
                            <div className="btn-luxury-primary-inner" />
                        </button>
                    </form>

                    {mode === 'login' && (
                        <div className="mt-8 text-center">
                            <button
                                onClick={() => setMode('forgot')}
                                className="text-xs uppercase tracking-widest text-warm-grey hover:text-charcoal transition-colors border-b border-transparent hover:border-warm-grey pb-0.5"
                            >
                                Forgot Password?
                            </button>
                        </div>
                    )}

                    {mode === 'forgot' && (
                        <div className="mt-8 text-center">
                            <button
                                onClick={() => setMode('login')}
                                className="text-xs uppercase tracking-widest text-warm-grey hover:text-charcoal transition-colors"
                            >
                                Back to Login
                            </button>
                        </div>
                    )}

                    {message && (
                        <div className={`mt-8 p-4 border text-center text-xs font-serif italic ${message.includes('check') || message.includes('updated')
                            ? 'border-green-800 text-green-900 bg-green-50'
                            : 'border-red-200 text-red-900 bg-red-50'
                            }`}>
                            {message}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
