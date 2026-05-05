import React, { lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { VisualMoodProvider } from './context/VisualMoodContext';
import { RootLayout } from './components/RootLayout';

const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));
const ChatPage = lazy(() => import('./pages/ChatPage').then(m => ({ default: m.ChatPage })));
const PracticePage = lazy(() => import('./pages/PracticePage').then(m => ({ default: m.PracticePage })));
const CoordinadorLoginPage = lazy(() => import('./pages/CoordinadorLoginPage').then(m => ({ default: m.CoordinadorLoginPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const LandingPage = lazy(() => import('./pages/LandingPage').then(m => ({ default: m.LandingPage })));

// Guard: solo estudiantes autenticados
const StudentRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, role } = useAuth();
  if (!isAuthenticated || role !== 'student') return <Navigate to="/login" replace />;
  return <>{children}</>;
};

// Guard: solo coordinadores autenticados
const CoordinatorRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, role } = useAuth();
  if (!isAuthenticated || role !== 'coordinator') return <Navigate to="/coordinador" replace />;
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      {/* RootLayout wraps ALL routes — Canvas persists across navigation */}
      <Route element={<RootLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/coordinador" element={<CoordinadorLoginPage />} />

        {/* Rutas protegidas — estudiante */}
        <Route path="/chat" element={<StudentRoute><ChatPage /></StudentRoute>} />
        <Route path="/practica" element={<StudentRoute><PracticePage /></StudentRoute>} />

        {/* Rutas protegidas — coordinador */}
        <Route path="/coordinador/dashboard" element={<CoordinatorRoute><DashboardPage /></CoordinatorRoute>} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <VisualMoodProvider>
            <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
            <AppRoutes />
          </VisualMoodProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
