import { useAuth } from "../context/AuthContext";

const BASE_URL = "http://localhost:8000";

export function useApi() {
  const { token } = useAuth();

  const request = async (
    path,
    { method = "GET", body, headers = {}, ...opts } = {}
  ) => {
    const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(BASE_URL + path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...authHeader,
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    });

    if (res.status === 204) {
      return;
    }

    let data;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      const error = data?.detail ?? data ?? `Error ${res.status}`;
      throw error;
    }

    return data;
  };

  return {
    get:    (path)       => request(path, { method: "GET" }),
    post:   (path, body) => request(path, { method: "POST",   body }),
    put:    (path, body) => request(path, { method: "PUT",    body }),
    delete: (path)       => request(path, { method: "DELETE" }),
  };
}
