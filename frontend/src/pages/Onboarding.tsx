import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';
import { ArrowRight } from 'lucide-react';

export default function Onboarding() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);

    const [formData, setFormData] = useState({
        full_name: '',
        interests: '',
        briefing_time: '07:00'
    });

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const { error } = await supabase
                .from('profiles')
                .upsert({
                    id: user?.id,
                    full_name: formData.full_name,
                    interests: formData.interests,
                    briefing_time: formData.briefing_time,
                    updated_at: new Date()
                });

            if (error) throw error;
            navigate('/');
        } catch (error) {
            alert('Error updating profile: ' + (error as Error).message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-alabaster">
            <div className="w-full max-w-lg">
                <div className="mb-16 text-center">
                    <h1 className="text-4xl font-serif text-charcoal mb-4">Willkommen.</h1>
                    <p className="text-warm-grey font-serif italic">Richten wir Ihre tägliche Intelligenz ein.</p>
                </div>

                <div className="card-luxury p-12">
                    <form onSubmit={handleUpdateProfile} className="space-y-12">
                        {/* Name */}
                        <div>
                            <label className="block text-xs uppercase tracking-widest text-warm-grey mb-4">
                                Wie dürfen wir Sie nennen?
                            </label>
                            <input
                                type="text"
                                className="input-luxury text-2xl"
                                placeholder="z.B. Joshua"
                                value={formData.full_name}
                                onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                                required
                            />
                        </div>

                        {/* Interests */}
                        <div>
                            <label className="block text-xs uppercase tracking-widest text-warm-grey mb-4">
                                Hauptinteressen
                            </label>
                            <textarea
                                className="w-full bg-transparent border-b border-charcoal/20 py-2 font-serif text-lg outline-none focus:border-charcoal transition-colors min-h-[80px]"
                                placeholder="z.B. KI, Weltwirtschaft, Design..."
                                value={formData.interests}
                                onChange={e => setFormData({ ...formData, interests: e.target.value })}
                            />
                        </div>

                        {/* Time */}
                        <div>
                            <label className="block text-xs uppercase tracking-widest text-warm-grey mb-4">
                                Briefing Zeitplan
                            </label>
                            <input
                                type="time"
                                className="input-luxury text-2xl"
                                value={formData.briefing_time}
                                onChange={e => setFormData({ ...formData, briefing_time: e.target.value })}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-luxury-primary group w-full flex items-center justify-center gap-4 mt-8"
                        >
                            <div className="btn-luxury-primary-inner" />
                            <span className="relative z-10">{loading ? 'Speichert...' : 'Einrichtung abschließen'}</span>
                            <ArrowRight className="w-4 h-4 relative z-10" />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
