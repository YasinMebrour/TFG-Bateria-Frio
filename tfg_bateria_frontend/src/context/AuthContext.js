// src/context/AuthContext.jsx
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  isTokenValid,
  tokenRemainingSeconds,
} from "../utils/auth";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

const AuthContext = createContext(null);

export function AuthProvider({ children, setQueryClientVersion }) {
  const navigate = useNavigate();
  /* ---------- estado ---------- */
  const [token, setToken] = useState(() => {
    const t = localStorage.getItem("token");
    return isTokenValid(t) ? t : null;
  });
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);

  const queryClient = useQueryClient();

  /* ---------- login ---------- */
  const login = async (username, password) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch("http://localhost:8000/auth/login", {
      method: "POST",
      body,
    });
    if (!res.ok) throw new Error("Credenciales inválidas");

    const { access_token } = await res.json();
    localStorage.setItem("token", access_token);
    setToken(access_token);
  };

  function clearAppLocalStorage() {
    const prefixes = [
      "sliderManual_",
      "manualPrediction_",
      "manualIntervals_",
    ];
    for (const key of Object.keys(localStorage)) {
      if (prefixes.some(p => key.startsWith(p))) {
        localStorage.removeItem(key);
      }
    }
    // Si usaste un nombre personalizado para el persister:
    localStorage.removeItem("reactQueryCache");
    // Y, por supuesto, el token:
    localStorage.removeItem("token");
  }


  /* ---------- logout ---------- */
  const logout = () => {
    queryClient.clear();                 // memoria
    localStorage.removeItem("REACT_QUERY_OFFLINE_CACHE"); // por si acaso
    clearAppLocalStorage();              // ← aquí
    setToken(null);
    setUser(null);
    setQueryClientVersion(v => v + 1);
    navigate("/login", { replace: true });
  };


  /* ---------- rehidratación del usuario ---------- */
  useEffect(() => {
    if (!token) {
      setLoadingUser(false);
      return;
    }

    (async () => {
      try {
        const res = await fetch("http://localhost:8000/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setUser(await res.json());
      } catch (err) {
        console.error("[Auth] token inválido o backend caído:", err);
        logout();
      } finally {
        setLoadingUser(false);
      }
    })();
  }, [token]);

  /* ---------- expiración exacta ---------- */
  useEffect(() => {
    if (!token) return;

    const secs = tokenRemainingSeconds(token);
    if (secs <= 0) {
      logout();
      return;
    }
    const timer = setTimeout(logout, secs * 1000);
    return () => clearTimeout(timer);
  }, [token]);

  const authFetch = useCallback(
    (input, init = {}) => {
      if (!token) return Promise.reject(new Error("Sin token"));
      return fetch(input, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...init.headers,
        },
      });
    },
    [token]
  );

  return (
    <AuthContext.Provider
      value={{ token, user, login, logout, loadingUser, authFetch }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* ---------- hook de conveniencia ---------- */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx)
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
