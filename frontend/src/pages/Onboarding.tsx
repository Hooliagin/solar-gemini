import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';
import { ArrowRight, Clock, User, Sparkles } from 'lucide-react';

export default function Onboarding() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState(1);

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
        <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-black text-white">
            <div className="w-full max-w-lg">
                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-bold mb-2">Welcome! 👋</h1>
                    <p className="text-gray-400">Let's personalize your Daily Manager.</p>
                </div>

                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl">
                    <form onSubmit={handleUpdateProfile} className="space-y-6">
                        {/* Name */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                                <User className="w-4 h-4" /> What should we call you?
                            </label>
                            <input
                                type="text"
                                className="w-full bg-black border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                                placeholder="e.g. Josh"
                                value={formData.full_name}
                                onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                                required
                            />
                        </div>

                        {/* Interests */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                                <Sparkles className="w-4 h-4" /> Interests (for news briefing)
                            </label>
                            <textarea
                                className="w-full bg-black border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all min-h-[100px]"
                                placeholder="e.g. AI, Crypto, Local Weather in Berlin..."
                                value={formData.interests}
                                onChange={e => setFormData({ ...formData, interests: e.target.value })}
                            />
                        </div>

                        {/* Time */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                                <Clock className="w-4 h-4" /> When do you want your briefing?
                            </label>
                            <input
                                type="time"
                                className="w-full bg-black border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                                value={formData.briefing_time}
                                onChange={e => setFormData({ ...formData, briefing_time: e.target.value })}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-4 bg-blue-600 hover:bg-blue-700 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-2 mt-4"
                        >
                            {loading ? 'Saving...' : 'Get Started'} <ArrowRight className="w-5 h-5" />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
