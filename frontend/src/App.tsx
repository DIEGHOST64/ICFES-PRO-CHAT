import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { ChatPage } from './pages/ChatPage';
import { PracticePage } from './pages/PracticePage';
import { CoordinadorLoginPage } from './pages/CoordinadorLoginPage';
import { DashboardPage } from './pages/DashboardPage';

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
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/coordinador" element={<CoordinadorLoginPage />} />

      {/* Rutas protegidas — estudiante */}
      <Route path="/chat" element={<StudentRoute><ChatPage /></StudentRoute>} />
      <Route path="/practica" element={<StudentRoute><PracticePage /></StudentRoute>} />

      {/* Rutas protegidas — coordinador */}
      <Route path="/coordinador/dashboard" element={<CoordinatorRoute><DashboardPage /></CoordinatorRoute>} />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
