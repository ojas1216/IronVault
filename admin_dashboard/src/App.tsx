import React, { Component, ReactNode } from 'react';

class RootErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error)
      return (
        <div className="flex items-center justify-center h-screen bg-gray-100">
          <div className="bg-white rounded-xl shadow p-8 max-w-md text-center">
            <p className="text-red-600 font-semibold text-lg mb-2">Something went wrong</p>
            <p className="text-gray-500 text-sm mb-4">{(this.state.error as Error).message}</p>
            <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={() => window.location.href = '/dashboard'}>
              Back to Dashboard
            </button>
          </div>
        </div>
      );
    return this.props.children;
  }
}
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { DeviceDetailPage } from './pages/DeviceDetailPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { SimAlertsPage } from './pages/SimAlertsPage';
import { Sidebar } from './components/Sidebar';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
});

const ProtectedLayout: React.FC = () => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export const App: React.FC = () => (
  <RootErrorBoundary>
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/devices/:id" element={<DeviceDetailPage />} />
          <Route path="/sim-alerts" element={<SimAlertsPage />} />
          <Route path="/audit-logs" element={<AuditLogsPage />} />
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
  </RootErrorBoundary>
);
