// ===============================
// File: src/components/ChartsEnergia.jsx
// ===============================

import React, { useState, useEffect, useMemo } from 'react';
import Plot                       from 'plotly.js-basic-dist';
import createPlotlyComponent      from 'react-plotly.js/factory';
import '../../assets/styles/Charts.css';
import { useEnergia }             from '../../hooks/useEnergia';

const Plotly   = createPlotlyComponent(Plot);
const DATE_FMT = { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' };

export default function ChartsEnergia({
  focusDate,
  disableFetch = false,
  ahorroActivo = [],
  ahorroOpt = [],
}) {
  // ======== 1) Obtención + caché + diff incremental (último minuto) ========
  const {
    data:       series = { precioReal: [], precioPred: [], consumo: [] },
    isLoading,
    error,
  } = useEnergia(focusDate, disableFetch);

  // ======== 2) Control del rango X según focusDate ==========================
  const [range, setRange] = useState({ start: null, end: null });
  useEffect(() => {
    if (isLoading || !focusDate) return;
    const start = new Date(`${focusDate}T00:00:00`);
    const end   = new Date(`${focusDate}T23:59:59`);
    setRange({ start, end });
  }, [isLoading, focusDate]);

  const onRelayout = ({ 'xaxis.range[0]': s, 'xaxis.range[1]': e }) => {
    if (s && e) setRange({ start: new Date(s), end: new Date(e) });
  };

  // ======== 3) Configuración de gráficos (memoizados para no recalcular ====
  const CHARTS = useMemo(() => ([
    {
      title:  'Precio luz',
      unit:   '€/kWh',
      traces: [
        { key: 'precioReal', name: 'Real',       color: '#1f77b4', dash: null },
        { key: 'precioPred', name: 'Predicción', color: '#2ca02c', dash: 'dot' }
      ]
    },
    {
      title:  'Consumo',
      unit:   'W',
      traces: [
        { key: 'consumo',    name: 'Consumo',    color: '#d62728', dash: null }
      ]
    }
  ]), []);

  const BASE_LAYOUT = useMemo(() => ({
    xaxis: {
      type: 'date',
      range: [range.start, range.end],
      rangeslider: { visible: true },
      rangeselector: {
        buttons: [
          { count: 1,  label: '1h',  step: 'hour', stepmode: 'backward' },
          { count: 6,  label: '6h',  step: 'hour', stepmode: 'backward' },
          { count: 12, label: '12h', step: 'hour', stepmode: 'backward' },
          { count: 1,  label: '1d',  step: 'day',  stepmode: 'backward' },
          { step: 'all' }
        ]
      }
    },
    template:  'plotly_white',
    hovermode: 'x unified',
    margin:    { t: 40, b: 40, l: 60, r: 30 },
    height:    400
  }), [range]);

  // ======== 4) Estados de carga / error =====================================
  if (isLoading) {
    return <div className="spinner-container"><div className="spinner" /></div>;
  }
  if (error) {
    return <div className="error">{error.message || 'Error cargando datos'}</div>;
  }


  // Función para obtener shapes a partir de los intervalos
  function buildAhorroShapes(intervals, color, opacity = 0.15) {
    // intervals es un array de objetos: {start, end} en minutos (ej: 480-1020)
    if (!Array.isArray(intervals)) return [];
    return intervals.map(({ start, end }, i) => {
      // Convertir a hora para el focusDate, formato: 'YYYY-MM-DDTHH:mm:ss'
      const d = focusDate;
      const hour = m => String(Math.floor(m / 60)).padStart(2, '0');
      const min = m => String(m % 60).padStart(2, '0');
      const from = `${d}T${hour(start)}:${min(start)}:00`;
      const to   = `${d}T${hour(end)}:${min(end)}:00`;

      return {
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: from,
        x1: to,
        y0: 0,
        y1: 1,
        fillcolor: color,
        opacity: opacity,
        line: { width: 0 },
        layer: 'below',
        editable: false,
      };
    });
  }

  // Define los shapes (ahorro activo: azul, optimizado: verde)
  const shapesAhorroActivo = buildAhorroShapes(ahorroActivo, 'rgba(2, 238, 255, 0.73)', 0.28);
  const shapesAhorroOpt    = buildAhorroShapes(ahorroOpt,    'rgba(239, 255, 17, 0.73)', 0.28);

  // ======== 5) Renderizar los gráficos =====================================
   return (
    <div className="charts-container">
      <div style={{ display: 'flex', gap: 24, alignItems: 'center', margin: '8px 0 8px 10px' }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500,
        }}>
          <span style={{
            width: 24, height: 10, background: 'rgba(2, 238, 255, 0.73)', opacity: 0.73, border: '1px rgba(2, 238, 255, 0.73)',
            display: 'inline-block', borderRadius: 2
          }} />
          Ahorro activo
        </span>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500,
        }}>
          <span style={{
            width: 24, height: 10, background: 'rgba(239, 255, 17, 0.73)', opacity: 0.50, border: '1px rgba(239, 255, 17, 0.73)',
            display: 'inline-block', borderRadius: 2
          }} />
          Ahorro optimizado
        </span>
      </div>

      {CHARTS.map(({ title, unit, traces }) => (
        <Plotly
          key={title}
          data={traces.map(({ key, name, color, dash }) => ({
            x:    series[key].map(p => p.x),
            y:    series[key].map(p => p.y),
            type: 'scatter',
            mode: 'lines',
            name,
            line: key.startsWith('precio')
              ? { color, dash, shape: 'hv' }
              : { color, dash },
            hovertemplate: `<b>%{x|${DATE_FMT}}</b><br>${name}: %{y:.3f}<extra></extra>`
          }))}
          layout={{
            ...BASE_LAYOUT,
             showlegend: true,
              legend: {
                x: 0.98,           // 0 (izquierda) a 1 (derecha)
                y: 0.98,           // 0 (abajo) a 1 (arriba)
                xanchor: 'right',  // anclaje horizontal respecto a x
                yanchor: 'top',    // anclaje vertical respecto a y
                bgcolor: 'rgba(255, 255, 255, 0)', // fondo semitransparente opcional
              },
            title: { text: title, font: { size: 18 } },
            yaxis: { title: { text: `${title} (${unit})`, standoff: 20 } },
            shapes: [
              ...shapesAhorroOpt,    // primero optimizado (debajo)
              ...shapesAhorroActivo, // encima el activo
            ],
          }}
          onRelayout={onRelayout}
          useResizeHandler
          style={{ width: '100%', minHeight: '400px' }}
        />
      ))}
    </div>
  );
}
