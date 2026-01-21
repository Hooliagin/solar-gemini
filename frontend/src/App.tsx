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

// Main Layout for authenticated users
const Dashboard = () => {
  return (
    <div className="min-h-screen bg-black text-white p-6 pb-24">
      <header className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Daily Manager</h1>
        <div className="w-10 h-10 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-sm font-bold bg-gradient-to-br from-purple-500 to-blue-500">
          ME
        </div>
      </header>

      <main className="space-y-12">
        <section>
          <h2 className="text-xl font-semibold mb-4 text-gray-300">Morning Briefing</h2>
          <Player />
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4 text-gray-300">Evening Log</h2>
          <Recorder onUploadComplete={() => window.location.reload()} />
        </section>
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
