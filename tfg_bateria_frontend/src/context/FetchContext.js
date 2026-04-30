import React, { createContext, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { useLoading } from "./LoadingContext";
import { isTokenValid } from "../utils/auth";

const FetchContext = createContext(null);

export function FetchProvider({ children }) {
  const { token, logout }   = useAuth();
  const { startLoading, stopLoading } = useLoading();

  useEffect(() => {
    const original = window.fetch;

    window.fetch = async (input, init = {}) => {
      startLoading();
      try {
        if (token && !isTokenValid(token)) {
          logout();
          throw new Error("Token expirado");
        }

        const headers = new Headers(init.headers || {});
        if (token && !headers.has("Authorization")) {
          headers.set("Authorization", `Bearer ${token}`);
        }

        const res = await original(input, { ...init, headers });
        if (res.status === 401) logout();
        return res;
      } catch (err) {
        console.error("[fetch] fallo de red:", err);
        logout();
        throw err;
      } finally {
        stopLoading();
      }
    };

    return () => { window.fetch = original; };
  }, [token, logout, startLoading, stopLoading]);

  return <FetchContext.Provider value={null}>{children}</FetchContext.Provider>;
}