
import { ShieldAlert, LogOut } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useNavigate } from 'react-router-dom';

export default function ApprovalPending() {
    const navigate = useNavigate();

    const handleLogout = async () => {
        await supabase.auth.signOut();
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-stone-900 flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-stone-800 border border-stone-700 rounded-2xl p-8 text-center space-y-6 shadow-2xl">
                <div className="w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center mx-auto">
                    <ShieldAlert className="w-8 h-8 text-amber-500" />
                </div>

                <h1 className="text-2xl font-serif font-bold text-stone-100">
                    Wartet auf Freigabe
                </h1>

                <p className="text-stone-400 leading-relaxed">
                    Dein Account wurde erstellt, muss aber noch von einem Administrator freigeschaltet werden, bevor du Zugriff erhältst.
                </p>

                <div className="bg-stone-900/50 p-4 rounded-lg border border-stone-800 text-sm text-stone-500">
                    <p>Status: <span className="text-amber-500 font-semibold uppercase tracking-wider">Ausstehend</span></p>
                </div>

                <button
                    onClick={handleLogout}
                    className="w-full py-3 px-4 bg-stone-700 hover:bg-stone-600 text-stone-200 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
                >
                    <LogOut className="w-4 h-4" />
                    Abmelden
                </button>
            </div>
        </div>
    );
}
