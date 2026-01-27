import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import { Sparkles } from 'lucide-react';

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

// Main App Component with Routing
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/update-password" element={<AuthPage />} />
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />

          {/* Main Dashboard */}
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />

          {/* Settings Page */}
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
