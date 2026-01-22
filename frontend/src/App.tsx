import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Recorder from './components/Recorder';
import Player from './components/Player';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { session, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-black flex items-center justify-center text-white">Loading...</div>;
  if (!session) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

import InterestManager from './components/InterestManager';
import SettingsPanel from './components/SettingsPanel';
import { Sparkles, Mic, Play, LogOut } from 'lucide-react';

// Main Layout for authenticated users
const Dashboard = () => {
  const { signOut } = useAuth();

  return (
    <div className="min-h-screen text-white p-6 pb-24 max-w-7xl mx-auto">
      <header className="flex justify-between items-center mb-12">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl shadow-lg shadow-purple-500/20">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            Daily Manager
          </h1>
        </div>
        <button
          onClick={signOut}
          className="btn-icon"
          title="Sign Out"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Column: Morning Briefing */}
        <section className="space-y-6">
          <div className="flex items-center gap-2 mb-4">
            <Play className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-medium text-gray-200">Morning Briefing</h2>
          </div>
          <div className="glass-panel rounded-2xl p-6 min-h-[200px] flex flex-col justify-center transition-all hover:bg-white/5">
            <Player />
          </div>
        </section>

        {/* Right Column: Evening Log, Interests & Settings */}
        <div className="space-y-8">
          <section className="space-y-6">
            <div className="flex items-center gap-2 mb-4">
              <Mic className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-medium text-gray-200">Evening Log</h2>
            </div>
            <div className="glass-panel rounded-2xl p-6 transition-all hover:bg-white/5">
              <Recorder onUploadComplete={() => window.location.reload()} />
            </div>
          </section>

          <section>
            <InterestManager />
          </section>

          <section>
            <SettingsPanel />
          </section>
        </div>
      </main>
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
