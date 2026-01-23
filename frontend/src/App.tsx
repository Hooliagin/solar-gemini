import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Recorder from './components/Recorder';
import Player from './components/Player';
import InterestManager from './components/InterestManager';
import SettingsPanel from './components/SettingsPanel';
import { Sparkles, Mic, Play, LogOut, Sun, Moon } from 'lucide-react';
import { API_BASE_URL } from './config';
import { useSearchParams } from 'react-router-dom';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { session, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 animate-pulse-slow flex items-center justify-center">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <p className="text-gray-400 animate-pulse">Loading...</p>
      </div>
    </div>
  );
  if (!session) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

// Main Dashboard Layout
const Dashboard = () => {
  const { signOut, session } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const claimCode = searchParams.get('claim_code');
  const [userName, setUserName] = React.useState<string>('');

  React.useEffect(() => {
    if (claimCode && session?.access_token) {
      mergeAccount(claimCode, session.access_token);
    }
  }, [claimCode, session]);

  // Fetch user name
  React.useEffect(() => {
    const fetchUserName = async () => {
      try {
        const token = session?.access_token;
        if (!token) return;
        const res = await fetch(`${API_BASE_URL}/settings/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUserName(data.name || '');
        }
      } catch (error) {
        console.error('Failed to fetch user name', error);
      }
    };
    fetchUserName();
  }, [session]);

  const mergeAccount = async (code: string, token: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/settings/merge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ link_code: code })
      });
      const data = await res.json();
      if (res.ok) {
        alert(`✅ Account erfolgreich verknüpft! ${data.merged_items} Elemente wurden übertragen.`);
        searchParams.delete('claim_code');
        setSearchParams(searchParams);
      } else if (data.status === 'same_user') {
        // Ignore
      } else {
        alert(`Fehler beim Verknüpfen: ${data.detail || 'Unbekannter Fehler'}`);
      }
    } catch (e) {
      console.error(e);
      alert("Verbindungsfehler beim Account-Merge.");
    }
  };

  const getTimeOfDay = () => {
    const hour = new Date().getHours();
    if (hour < 12) return { greeting: "Guten Morgen", icon: Sun, period: "morning" };
    if (hour < 18) return { greeting: "Guten Tag", icon: Sun, period: "afternoon" };
    return { greeting: "Guten Abend", icon: Moon, period: "evening" };
  };

  const timeInfo = getTimeOfDay();
  const TimeIcon = timeInfo.icon;

  return (
    <div className="min-h-screen text-white">
      {/* Decorative Background Elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 -left-32 w-96 h-96 bg-purple-500/20 rounded-full blur-[128px] animate-pulse-slow" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-blue-500/20 rounded-full blur-[128px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <header className="flex justify-between items-center mb-12 animate-fade-in-up">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl shadow-lg shadow-purple-500/25 glow-purple">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold gradient-text">
                Daily Manager
              </h1>
              <p className="text-sm text-gray-500">Dein KI-Morgenassistent</p>
            </div>
          </div>
          <button
            onClick={signOut}
            className="btn-icon"
            title="Abmelden"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </header>

        {/* Welcome Section */}
        <section className="mb-12 animate-fade-in-up stagger-1">
          <div className="glass-card p-8 flex items-center gap-6">
            <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg">
              <TimeIcon className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-white mb-1">
                {timeInfo.greeting}{userName ? `, ${userName}` : ''}! 👋
              </h2>
              <p className="text-gray-400">
                {timeInfo.period === 'morning'
                  ? 'Bereit für dein personalisiertes Morgen-Briefing?'
                  : timeInfo.period === 'afternoon'
                    ? 'Zeit für ein Update? Hör dir dein Briefing an.'
                    : 'Vergiss nicht, dein Tagebuch für heute einzusprechen!'}
              </p>
            </div>
          </div>
        </section>

        {/* Main Content Grid */}
        <main className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Briefing */}
          <div className="space-y-8">
            <section className="animate-fade-in-up stagger-2">
              <div className="section-title">
                <Play className="w-4 h-4 text-purple-400" />
                <span>Morgen-Briefing</span>
              </div>
              <div className="glass-card p-6">
                <Player />
              </div>
            </section>

            <section className="animate-fade-in-up stagger-3">
              <div className="section-title">
                <Mic className="w-4 h-4 text-blue-400" />
                <span>Tagebuch</span>
              </div>
              <div className="glass-card p-6">
                <Recorder onUploadComplete={() => window.location.reload()} />
              </div>
            </section>
          </div>

          {/* Right Column: Settings & Interests */}
          <div className="space-y-8">
            <section className="animate-fade-in-up stagger-3">
              <InterestManager />
            </section>

            <section className="animate-fade-in-up stagger-4">
              <SettingsPanel />
            </section>
          </div>
        </main>

        {/* Footer */}
        <footer className="mt-16 text-center text-gray-600 text-sm animate-fade-in stagger-4">
          <p>Made with ❤️ for better mornings</p>
        </footer>
      </div>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
