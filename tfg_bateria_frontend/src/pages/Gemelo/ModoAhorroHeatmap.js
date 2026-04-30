import React, { useEffect, useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { DateTime } from 'luxon';
import { useApi } from '../../hooks/useApi';

const BUCKET      = 'CAMARA_2';
const MEASUREMENT = 'consumo';
const FIELD       = 'consumo_watios';

const HOURS       = 24;
const rowHeightPx = 35; // Alto por fila

// Calcula el lunes y los 7 días de la semana ISO que contiene selectedDate
const buildWeekDays = (isoDate) => {
  const monday = DateTime.fromISO(isoDate, { zone: 'Europe/Madrid' }).startOf('week');
  return Array.from({ length: 7 }, (_, i) =>
    monday.plus({ days: i }).toISODate()
  );
};

// Devuelve { start, stop } con zona UTC+2 para la semana ISO de `isoDate`
// Devuelve { start, stop } en local Europe/Madrid con offset correcto para esa semana
const buildWeekBoundsMadrid = (isoDate) => {
  // Siempre en zona Madrid local
  const base  = DateTime.fromISO(isoDate, { zone: 'Europe/Madrid' });
  const iniL  = base.startOf('week');         // lunes 00:00 local
  const finL  = iniL.plus({ weeks: 1 });      // lunes sig. 00:00 local

  return {
    start: iniL.toISO({ suppressMilliseconds: true }), // offset automático (puede ser +01:00 o +02:00)
    stop:  finL.toISO({ suppressMilliseconds: true })
  };
};


// Convierte puntos Influx → matriz por día con promedio horario (24 celdas)
const transformInfluxToHeatmap = (points = []) => {
  const rows = new Map(); // key = 'YYYY-MM-DD' → [{sum,n},…]
  points.forEach(({ time, value }) => {
    const dt  = DateTime.fromISO(time).setZone('Europe/Madrid');
    const day = dt.toISODate();
    const h   = dt.hour;

    if (!rows.has(day)) {
      rows.set(day, Array.from({ length: HOURS }, () => ({ sum: 0, n: 0 })));
    }
    const cell = rows.get(day)[h];
    cell.sum += value;
    cell.n   += 1;
  });

  return Array.from(rows.entries())
    .sort(([d1], [d2]) => new Date(d1) - new Date(d2))
    .map(([dia, vals]) => ({
      dia,
      valores: vals.map(({ sum, n }) => (n ? sum / n : null))
    }));
};

const ConsumoHeatmap = ({ selectedDate }) => {
  const [heatData, setHeatData] = useState([]);

  const api = useApi();

  useEffect(() => {
    if (!selectedDate) return;

    (async () => {
      try {
        const { start, stop } = buildWeekBoundsMadrid(selectedDate);


        const params = new URLSearchParams({
          bucket: BUCKET,
          measurement: MEASUREMENT,
          field: FIELD,
          start,
          stop
        });

        const json = await api.get(`/influx/data?${params}`);
        const transformed = transformInfluxToHeatmap(json.data);

        // ------- Completa los 7 días --------
        const fullWeekDays = buildWeekDays(selectedDate);
        const byDay = new Map(transformed.map(r => [r.dia, r.valores]));
        const completed = fullWeekDays.map(dia => ({
          dia,
          valores: byDay.get(dia) ?? Array(HOURS).fill(null)
        }));

        setHeatData(completed);
      } catch (err) {
        console.error('Consumo semanal:', err);
        // Asegura que se muestren 7 días vacíos si error
        const emptyWeek = buildWeekDays(selectedDate).map(dia => ({
          dia,
          valores: Array(HOURS).fill(null)
        }));
        setHeatData(emptyWeek);
      }
    })();
  }, [selectedDate]);

  // Datos para Plotly
  const z        = heatData.map(d => d.valores);
  const yLabels  = heatData.map(d =>
    DateTime.fromISO(d.dia).setLocale('es').toFormat('ccc dd LLL')
  );
  const xLabels  = useMemo(() => Array.from({ length: HOURS }, (_, i) => i), []);
  const timeLabels = useMemo(
    () => xLabels.map(h => `${String(h).padStart(2, '0')}:00`),
    [xLabels]
  );
  const customData = useMemo(() => z.map(() => timeLabels), [z, timeLabels]);
  const plotHeight = 7 * rowHeightPx + 100; // Siempre 7 filas

  return (
    <div className="consumo-heatmap w-full">
      <h4 className="text-center mb-2">Mapa de Calor – Consumo semanal</h4>

      <Plot
        data={[{
          z,
          x: xLabels,
          y: yLabels,
          customdata: customData,
          type: 'heatmap',
          colorscale: 'Viridis',
          showscale: true,
          hovertemplate:
            'Hora %{customdata}<br>Día %{y}<br>kW %{z:.2f}<extra></extra>'
        }]}
        layout={{
          dragmode: 'pan',
          autosize: true,
          height: plotHeight,
          margin: { l: 90, r: 30, t: 30, b: 50 },
          yaxis: { type: 'category', autorange: 'reversed', title: 'Día' },
          xaxis: {
            title: 'Hora',
            tickmode: 'array',
            tickvals: [0, 6, 12, 18, 23],
            ticktext: ['0:00', '6:00', '12:00', '18:00', '23:00'],
            tickfont: { size: 8 }
          }
        }}
        config={{ responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
};

export default ConsumoHeatmap;
