import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import WeeklyDashboard from './pages/WeeklyDashboard';
import Settings from './pages/Settings';
import AdminDashboard from './pages/AdminDashboard';
// Imports removed

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { session, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-alabaster">
      <div className="flex flex-col items-center gap-6">
        <div className="w-12 h-12 border-2 border-charcoal border-t-transparent animate-spin rounded-full" />
        <p className="text-charcoal font-serif tracking-[0.2em] text-xs uppercase animate-pulse">Loading</p>
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

          <Route path="/weekly" element={<ProtectedRoute><WeeklyDashboard /></ProtectedRoute>} />

          {/* Settings Page */}
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />

          {/* Hidden Admin Portal - NOT linked in UI */}
          <Route path="/admin-portal-access" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
