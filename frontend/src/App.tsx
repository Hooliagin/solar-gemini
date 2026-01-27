import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Recorder from './components/Recorder';
import Player from './components/Player';
import InterestManager from './components/InterestManager';
import SettingsPanel from './components/SettingsPanel';
import DiaryList from './components/DiaryList';
import LoadingScreen from './components/LoadingScreen';
import { Sparkles, Mic, Play, LogOut, Sun, Moon, FileText } from 'lucide-react';
import { API_BASE_URL } from './config';
import { useSearchParams } from 'react-router-dom';

// Animation variants - MORE VISIBLE
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,  // Increased from 0.1
      delayChildren: 0.3     // Increased from 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 40, scale: 0.95 },  // Bigger movement + scale
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 200,  // Reduced for bouncier effect
      damping: 20      // Reduced for more bounce
    }
  }
};

const glowHover = {
  y: -8,        // Lift effect only
  boxShadow: "0 0 30px rgba(0, 255, 136, 0.6), 0 10px 40px rgba(0, 255, 136, 0.3)",  // Stronger glow
  transition: { type: "spring" as const, stiffness: 400, damping: 10 }
};

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
  const [isLoading, setIsLoading] = React.useState(true);
  const [refreshTrigger, setRefreshTrigger] = React.useState(0);

  const handleUploadComplete = () => {
    setRefreshTrigger(prev => prev + 1);
  };

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
        if (!token) {
          setIsLoading(false);
          return;
        }
        const res = await fetch(`${API_BASE_URL}/settings/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUserName(data.name || '');
        }
      } catch (error) {
        console.error('Failed to fetch user name', error);
      } finally {
        // Minimum loading time of 1.5s for smooth animation
        setTimeout(() => setIsLoading(false), 1500);
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
    <>
      <AnimatePresence mode="wait">
        {isLoading && <LoadingScreen key="loading" />}
      </AnimatePresence>

      {!isLoading && (
        <div className="min-h-screen text-white">
          {/* Decorative Background Elements */}
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-1/4 -left-32 w-96 h-96 bg-[var(--cyber-accent)]/10 rounded-full blur-[128px] animate-neon-pulse" />
            <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-[var(--cyber-secondary)]/10 rounded-full blur-[128px] animate-neon-pulse" style={{ animationDelay: '1s' }} />
            <div className="absolute top-3/4 left-1/2 w-64 h-64 bg-[var(--cyber-tertiary)]/10 rounded-full blur-[100px] animate-neon-pulse" style={{ animationDelay: '2s' }} />
          </div>

          <div className="relative z-10 max-w-7xl mx-auto px-4 py-8 md:px-8 md:py-12">
            {/* Header */}
            <header className="flex justify-between items-center mb-10 md:mb-20 animate-fade-in-up">
              <div className="flex items-center gap-4">
                <div className="p-3 border-2 border-[var(--cyber-accent)] glow-neon" style={{ clipPath: 'polygon(0 8px, 8px 0, calc(100% - 8px) 0, 100% 8px, 100% calc(100% - 8px), calc(100% - 8px) 100%, 8px 100%, 0 calc(100% - 8px))' }}>
                  <Sparkles className="w-7 h-7 text-[var(--cyber-accent)]" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold gradient-text tracking-widest cyber-glitch" data-text="DAILY MANAGER">
                    DAILY MANAGER
                  </h1>
                  <p className="text-xs text-[var(--cyber-text-muted)] font-mono tracking-wider">&gt; KI_MORGENASSISTENT.exe</p>
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
            <motion.section
              className="mb-12"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 100, damping: 20, delay: 0.1 }}
            >
              <motion.div
                className="glass-card p-10 flex items-center gap-8"
                whileHover={glowHover}
              >
                <motion.div
                  className="p-4 border-2 border-[var(--cyber-accent)] glow-neon"
                  style={{ clipPath: 'polygon(0 8px, 8px 0, calc(100% - 8px) 0, 100% 8px, 100% calc(100% - 8px), calc(100% - 8px) 100%, 8px 100%, 0 calc(100% - 8px))' }}
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  transition={{ type: "spring", stiffness: 400, damping: 10 }}
                >
                  <TimeIcon className="w-8 h-8 text-[var(--cyber-accent)]" />
                </motion.div>
                <div>
                  <h2 className="text-2xl font-bold text-[var(--cyber-accent)] mb-1 tracking-wide">
                    {timeInfo.greeting.toUpperCase()}{userName ? `, ${userName.toUpperCase()}` : ''} <span className="animate-blink">_</span>
                  </h2>
                  <p className="text-[var(--cyber-text-muted)] font-mono text-sm">
                    {timeInfo.period === 'morning'
                      ? '> Bereit für dein personalisiertes Morgen-Briefing?'
                      : timeInfo.period === 'afternoon'
                        ? '> Zeit für ein Update? Hör dir dein Briefing an.'
                        : '> Vergiss nicht, dein Tagebuch für heute einzusprechen!'}
                  </p>
                </div>
              </motion.div>
            </motion.section>

            {/* Main Content Grid */}
            <motion.main
              className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-12"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {/* Left Column: Briefing */}
              <div className="space-y-12">
                <motion.section variants={itemVariants}>
                  <div className="section-title">
                    <Play className="w-4 h-4 text-[var(--cyber-accent)]" />
                    <span>MORGEN_BRIEFING</span>
                  </div>
                  <motion.div
                    className="glass-card p-8"
                    whileHover={glowHover}
                  >
                    <Player />
                  </motion.div>
                </motion.section>

                <motion.section variants={itemVariants}>
                  <div className="section-title">
                    <Mic className="w-4 h-4 text-[var(--cyber-secondary)]" />
                    <span>TAGEBUCH</span>
                  </div>
                  <motion.div
                    className="glass-card p-8"
                    whileHover={glowHover}
                  >
                    <Recorder onUploadComplete={handleUploadComplete} />
                  </motion.div>
                </motion.section>

                <motion.section variants={itemVariants}>
                  <div className="section-title">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span>VERLAUF</span>
                  </div>
                  <div className="glass-card p-6 max-h-[400px] overflow-y-auto scrollbar-hide">
                    <DiaryList refreshTrigger={refreshTrigger} />
                  </div>
                </motion.section>
              </div>

              {/* Right Column: Settings & Interests */}
              <div className="space-y-12">
                <motion.section variants={itemVariants}>
                  <InterestManager />
                </motion.section>

                <motion.section variants={itemVariants}>
                  <SettingsPanel />
                </motion.section>
              </div>
            </motion.main>

            {/* Footer */}
            <motion.footer
              className="mt-24 text-center text-[var(--cyber-text-muted)] text-sm font-mono"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              <p>&gt; MADE_WITH_<span className="text-[var(--cyber-accent)]">❤</span>_FOR_BETTER_MORNINGS</p>
            </motion.footer>
          </div>
        </div>
      )}
    </>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/update-password" element={<AuthPage />} />
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
