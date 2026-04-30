// src/lib/api.js
import { useAuth } from "../context/AuthContext";

export function useApi() {
  const { token } = useAuth();

  const apiFetch = (url, options = {}) => {
    const headers = {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
    return fetch(url, { ...options, headers });
  };

  return apiFetch;
}
