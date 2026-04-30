
// ────────────────────────────────────────────────────────────────────────────────
// src/hooks/useChartData.js
// Igual que antes, pero la clave y la URL se generan a partir de dataStart/dataEnd
// (Date objects). No se actualiza cuando el usuario hace zoom en el cliente.
// ────────────────────────────────────────────────────────────────────────────────

import { useQueries } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { formatISO, startOfDay, endOfDay } from "date-fns";

/* Cache en memoria viva durante toda la sesión */
const rangeCache = new Map();

function getCacheKey(b, m, s, e, f) {
  return `${b}|${m}|${s}|${e}|${f}`;
}

export function useChartData(charts = [], dataStart, dataEnd) {
  const { authFetch } = useAuth();

  const startISO = formatISO(startOfDay(dataStart), { representation: "date" });
  const endISO = formatISO(startOfDay(dataEnd), { representation: "date" });

  return useQueries({
    queries: charts.map(chart => {
      const { bucket, measurement, field } = chart;
      const key = getCacheKey(bucket, measurement, startISO, endISO, field);

      return {
        queryKey: ["chartData", key],
        queryFn: async () => {
          const cached = rangeCache.get(key);
          if (cached?.data) return cached.data;
          if (cached?.promise) return cached.promise;

          const url =
            `${process.env.REACT_APP_API_URL}/influx/data` +
            `?bucket=${encodeURIComponent(bucket)}` +
            `&measurement=${encodeURIComponent(measurement)}` +
            `&field=${encodeURIComponent(field)}` +
            `&start=${startISO}T00:00:00Z` +
            `&stop=${endISO}T23:59:59Z`;

          const fetchPromise = authFetch(url)
            .then(res => {
              if (!res.ok) throw new Error(`Error ${res.status}`);
              return res.json();
            })
            .then(json => {
              rangeCache.set(key, { data: json.data });
              return json.data;
            })
            .catch(err => {
              rangeCache.delete(key);
              throw err;
            });

          rangeCache.set(key, { promise: fetchPromise });
          return fetchPromise;
        },
        enabled: Boolean(dataStart && dataEnd),
        staleTime: Infinity
      };
    })
  });
}
