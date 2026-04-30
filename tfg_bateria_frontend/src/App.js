import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider }   from "./context/AuthContext";
import { LoadingProvider } from "./context/LoadingContext";
import { FetchProvider }   from "./context/FetchContext";
import PrivateRoute from "./components/PrivateRoute";
import AdminRoute   from "./components/AdminRoute";
import LoadingOverlay from "./components/LoadingOverlay";


/* páginas */
import Dashboard from "./pages/Dashboard/Dashboard";
import Gemelo from "./pages/Gemelo/Gemelo";
import Config from "./pages/Configuracion/Configuracion";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage  from "./pages/ResetPasswordPage";
import Planificador from "./pages/Planificador/Planificador";
import Navbar from "./components/Navbar";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export default function App() {
  const [version, setVersion] = React.useState(0);
  const queryClient = React.useMemo(() => new QueryClient(), [version]);

  return (
    <Router>
      <AuthProvider setQueryClientVersion={setVersion}>
        <QueryClientProvider client={queryClient}>
          <LoadingProvider>
            <FetchProvider>
                <Navbar />
                <Routes>
                  {/* privadas */}
                  <Route path="/" element={<Navigate to="/gemelo" replace />} />
                  <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
                  <Route path="/gemelo" element={<PrivateRoute><Gemelo /></PrivateRoute>} />
                  <Route path="/planificador" element={<AdminRoute><Planificador /></AdminRoute>} />
                  {/* admin */}
                  <Route path="/config" element={<AdminRoute><Config /></AdminRoute>} />
                  {/* públicas */}
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                  <Route path="/reset-password" element={<ResetPasswordPage />} />
                </Routes>
              <LoadingOverlay />
            </FetchProvider>
          </LoadingProvider>
        </QueryClientProvider>
      </AuthProvider>
    </Router>
  );
}