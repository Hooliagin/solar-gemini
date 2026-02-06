import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import WeeklyDashboard from './pages/WeeklyDashboard';
import Settings from './pages/Settings';
import AdminDashboard from './pages/AdminDashboard';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
// Imports removed

import { API_BASE_URL } from './config';
import ApprovalPending from './pages/ApprovalPending';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { session, loading } = useAuth();
  const [isApproved, setIsApproved] = React.useState<boolean | null>(null);
  const [checkingApproval, setCheckingApproval] = React.useState(false);

  React.useEffect(() => {
    if (session?.access_token && isApproved === null) {
      setCheckingApproval(true);
      fetch(`${API_BASE_URL}/settings/`, {
        headers: { Authorization: `Bearer ${session.access_token}` }
      })
        .then(res => {
          if (res.ok) return res.json();
          throw new Error("Failed");
        })
        .then(data => {
          setIsApproved(!!data.is_approved);
        })
        .catch(() => {
          // e.g. Network error? Fallback to false or retry
          setIsApproved(false);
        })
        .finally(() => setCheckingApproval(false));
    }
  }, [session]);

  if (loading || (session && isApproved === null)) return (
    <div className="min-h-screen flex items-center justify-center bg-alabaster">
      <div className="flex flex-col items-center gap-6">
        <div className="w-12 h-12 border-2 border-charcoal border-t-transparent animate-spin rounded-full" />
        <p className="text-charcoal font-serif tracking-[0.2em] text-xs uppercase animate-pulse">Verifying Access</p>
      </div>
    </div>
  );

  if (!session) return <Navigate to="/login" replace />;
  if (isApproved === false) return <ApprovalPending />;

  return <>{children}</>;
};

// Main App Component with Routing
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Pages */}
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />

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
