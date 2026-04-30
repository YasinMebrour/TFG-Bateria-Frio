import { useQuery } from '@tanstack/react-query';
import { useAuth }  from '../context/AuthContext';

const API = 'http://localhost:8000';

/* ---------- utilidades comunes ---------------------------------------- */
const process = (ds = []) =>
  ds.map(i => ({ x: new Date(i.time), y: i.value }))
    .filter(d => !isNaN(d.x));                       // descarta fechas inválidas

export function useEnergia(focusDate, disableFetch = false) {
  const { authFetch } = useAuth();

  /* ----------- boundaries del día focus (UTC) ------------------------- */
  // admitimos `focusDate` como Date o como string 'YYYY-MM-DD'
  const focus      = typeof focusDate === 'string'
                       ? new Date(`${focusDate}T00:00:00`)
                       : new Date(focusDate);
  focus.setHours(0, 0, 0, 0);                       // 00:00 local
  const startISO   = focus.toISOString();           // inicio en UTC
  const stopISO    = new Date(focus.getTime() + 86_400_000).toISOString(); // +24 h

  /* ----------- react-query ------------------------------------------- */
  return useQuery({
    enabled: !disableFetch && Boolean(focusDate),
    queryKey: ['energia-series', focus.toDateString()],  // cache por día
    staleTime: Infinity,

    /* ------------------- queryFn (fetch diario completo) -------------- */
    queryFn: async () => {
      const qs = (bucket, measurement, field) =>
        `bucket=${encodeURIComponent(bucket)}` +
        `&measurement=${encodeURIComponent(measurement)}` +
        `&field=${encodeURIComponent(field)}` +
        `&start=${encodeURIComponent(startISO)}` +
        `&stop=${encodeURIComponent(stopISO)}`;

      /* fetch concurrente de las tres series --------------------------- */
      const [rReal, rPred, rCons] = await Promise.all([
        authFetch(`${API}/influx/data?${qs('TARIFF_PRICES','pvpc_prices','real_kwh_price')}`),
        authFetch(`${API}/influx/data?${qs('TARIFF_PRICES','pvpc_prices','predicted_kwh_price')}`),
        authFetch(`${API}/influx/data?${qs('CAMARA_2','consumo','consumo_watios')}`)
      ]);
      if (!rReal.ok || !rPred.ok || !rCons.ok) throw new Error('HTTP error');

      const [jsReal, jsPred, jsCons] = await Promise.all([
        rReal.json(), rPred.json(), rCons.json()
      ]);

      return {
        precioReal: process(jsReal.data),
        precioPred: process(jsPred.data),
        consumo:    process(jsCons.data),
      };
    }
  });
}
