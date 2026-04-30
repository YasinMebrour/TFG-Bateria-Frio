// ────────────────────────────────────────────────────────────────────────────────
// src/pages/Dashboard/Dashboard.js
// Versión con separación de rango de datos (dataStart/dataEnd) y rango visible 
// (viewStart/viewEnd) para evitar que Chart.js pierda el zoom al actualizar.
// ────────────────────────────────────────────────────────────────────────────────

import React, { useState, useRef, useEffect } from "react";
import { startOfDay, endOfDay, subDays, formatISO } from "date-fns";
import { useDebounce } from "use-debounce";
import Sidebar from "./Sidebar";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from "chart.js";
import "chartjs-adapter-date-fns";
import { useChartData } from "../../hooks/useChartData";
import "../../assets/styles/Dashboard.css";
import zoomPlugin from "chartjs-plugin-zoom";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  zoomPlugin
);

const STORAGE_KEY = "dashboard_charts";

export default function Dashboard() {
  // ─── Fechas para descarga de datos ──────────────────────────────────────────
  const today = startOfDay(new Date());
  const yesterday = startOfDay(subDays(new Date(), 1));

  // ─── Persistencia de tarjetas ───────────────────────────────────────────────
  const [charts, setCharts] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return [];
      const parsed = JSON.parse(saved);
      return parsed.charts || [];
    } catch {
      return [];
    }
  });

  const [viewStart, setViewStart] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return yesterday;
      const parsed = JSON.parse(saved);
      return parsed.viewStart ? new Date(parsed.viewStart) : yesterday;
    } catch {
      return yesterday;
    }
  });

  const [viewEnd, setViewEnd] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return endOfDay(today);
      const parsed = JSON.parse(saved);
      return parsed.viewEnd ? new Date(parsed.viewEnd) : endOfDay(today);
    } catch {
      return endOfDay(today);
    }
  });

  const [dataStart, setDataStart] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return yesterday;
      const parsed = JSON.parse(saved);
      return parsed.dataStart ? new Date(parsed.dataStart) : yesterday;
    } catch {
      return yesterday;
    }
  });

  const [dataEnd, setDataEnd] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return today;
      const parsed = JSON.parse(saved);
      return parsed.dataEnd ? new Date(parsed.dataEnd) : today;
    } catch {
      return today;
    }
  });
    useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        charts,
        viewStart,
        viewEnd,
        dataStart,
        dataEnd
      })
    );
  }, [charts, viewStart, viewEnd, dataStart, dataEnd]);

  // ─── Debounce para reducir llamada al backend ──────────────────────────────
  const [debDataStart] = useDebounce(dataStart, 300);
  const [debDataEnd] = useDebounce(dataEnd, 300);

  // ─── Referencia contenedor y estado hover para DnD ──────────────────────────
  const [isHovered, setIsHovered] = useState(false);
  const dashboardRef = useRef(null);

  // ─── Datos para las gráficas ────────────────────────────────────────────────
  const chartQueries = useChartData(charts, debDataStart, debDataEnd);

  // ─── Handlers drag & drop de tarjetas ───────────────────────────────────────
  const handleDragOver = e => {
    if (e.dataTransfer.types.includes("application/json")) e.preventDefault();
  };

  const handleDrop = e => {
    e.preventDefault();
    setIsHovered(false);
    if (!e.dataTransfer.types.includes("application/json")) return;
    let payload;
    try {
      payload = JSON.parse(e.dataTransfer.getData("application/json"));
    } catch {
      return;
    }
    const { bucket, measurement, field } = payload;
    if (!dashboardRef.current) return;
    const bounds = dashboardRef.current.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const y = e.clientY - bounds.top;
    setCharts(prev => [
      ...prev,
      { bucket, measurement, field, x, y, width: 300, height: 250 }
    ]);
  };

  // ─── Movimiento de tarjetas ────────────────────────────────────────────────
  const handleDragStart = (e, idx) => {
    if (e.target.tagName === "CANVAS" || e.target.closest("canvas")) return;
    e.preventDefault();
    document.body.style.userSelect = "none";
    const { clientX, clientY } = e;
    setCharts(prev =>
      prev.map((c, i) =>
        i === idx ? { ...c, isDragging: true, startX: clientX, startY: clientY } : c
      )
    );
    const move = ev => handleDragMove(ev, idx);
    const up = () => handleDragEnd(idx, move, up);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

  const handleDragMove = (e, idx) => {
    if (!dashboardRef.current) return;
    e.preventDefault();
    e.stopPropagation();
    setCharts(prev =>
      prev.map((c, i) => {
        if (i !== idx || !c.isDragging) return c;
        const dx = e.clientX - c.startX;
        const dy = e.clientY - c.startY;
        const bounds = dashboardRef.current.getBoundingClientRect();
        const newX = Math.max(0, Math.min(c.x + dx, bounds.width - c.width));
        const newY = Math.max(0, Math.min(c.y + dy, bounds.height - c.height));
        return { ...c, x: newX, y: newY, startX: e.clientX, startY: e.clientY };
      })
    );
  };

  const handleDragEnd = (idx, moveHandler, upHandler) => {
    document.body.style.userSelect = "auto";
    setCharts(prev => prev.map(c => (c.isDragging ? { ...c, isDragging: false } : c)));
    window.removeEventListener("mousemove", moveHandler);
    window.removeEventListener("mouseup", upHandler);
  };

  // ─── Redimensionado de tarjetas ────────────────────────────────────────────
  const handleResizeStart = (e, idx) => {
    e.stopPropagation();
    e.preventDefault();
    document.body.style.userSelect = "none";
    const startX = e.clientX;
    const startY = e.clientY;
    setCharts(prev =>
      prev.map((c, i) =>
        i === idx ? { ...c, isResizing: true, resizeStartX: startX, resizeStartY: startY } : c
      )
    );
    const move = ev => handleResizeMove(ev, idx);
    const up = () => handleResizeEnd(idx, move, up);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

  const handleResizeMove = (e, idx) => {
    e.preventDefault();
    e.stopPropagation();
    setCharts(prev =>
      prev.map((c, i) => {
        if (i !== idx || !c.isResizing) return c;
        const dx = e.clientX - c.resizeStartX;
        const dy = e.clientY - c.resizeStartY;
        return {
          ...c,
          width: Math.max(150, c.width + dx),
          height: Math.max(150, c.height + dy),
          resizeStartX: e.clientX,
          resizeStartY: e.clientY
        };
      })
    );
  };

  const handleResizeEnd = (idx, moveHandler, upHandler) => {
    document.body.style.userSelect = "auto";
    setCharts(prev => prev.map((c, i) => (i === idx ? { ...c, isResizing: false } : c)));
    window.removeEventListener("mousemove", moveHandler);
    window.removeEventListener("mouseup", upHandler);
  };

  // ─── Opciones de Chart.js ──────────────────────────────────────────────────
  const chartOptions = React.useMemo(() => ({
  animation: false,
  responsive: true,
  maintainAspectRatio: false,
  layout: { padding: 10 },

  plugins: {
    legend: { display: true, labels: { color: "black" } },

    zoom: {
      // límites “duros”: no dejes salir al usuario del rango descargado
      limits: {
        x: {
          min: dataStart.valueOf(),
          max: endOfDay(dataEnd).valueOf()
        }
      },

      // ─── DESPLAZAMIENTO ───────────────────────────
      pan: {
        enabled: true,
        mode: "x",
        onPanComplete: ({ chart }) => {
          const { min, max } = chart.scales.x;
          setViewStart(new Date(min));
          setViewEnd  (new Date(max));
        }
      },

      // ─── ZOOM ─────────────────────────────────────
      zoom: {
        wheel: { enabled: true },
        drag: {
          enabled: true,
          modifierKey: "shift",
          borderColor: "rgba(0,0,0,0.4)",
          borderWidth: 1,
          backgroundColor: "rgba(0,0,0,0.15)"
        },
        mode: "x",
        onZoomComplete: ({ chart }) => {
          const { min, max } = chart.scales.x;
          setViewStart(new Date(min));
          setViewEnd  (new Date(max));
        }
      }
    }
  },

  scales: {
    x: {
      type: "time",
      min: viewStart.valueOf(),
      max: viewEnd.valueOf(),

      time: {
        displayFormats: {
          hour:  "HH:mm",
          day:   "dd/MM/yyyy",
          month: "MMM yyyy"
        },
        tooltipFormat: "Pp"
      },
      grid: { display: true },
      ticks: {
        color: "black",
        major: { enabled: true },
        callback(value) {
          const d = new Date(value);
          return d.getHours() === 0 && d.getMinutes() === 0
            ? d.toLocaleDateString("es-ES")
            : d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
        }
      }
    },

    y: {
      type: "linear",
      title: { display: true, text: "Valor", color: "black" },
      ticks: { color: "black" }
    }
  }
}), [viewStart, viewEnd, dataStart, dataEnd]);


  // ─── Cambio desde los date-pickers ──────────────────────────────────────────
    const handlePickerChange = (setter, otherSetter) => e => {
    const newDate = startOfDay(new Date(e.target.value));
    setter(newDate);
    // Sincroniza la vista completa con el nuevo rango de datos
    if (otherSetter) {
      const start = e.target.name === "start" ? newDate : dataStart;
      const end = e.target.name === "end" ? newDate : dataEnd;
      setViewStart(startOfDay(start));
      setViewEnd(endOfDay(end));
    }
  };



  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="dashboard-wrapper">
      <Sidebar />

      <div
        ref={dashboardRef}
        className={`dashboard-container${isHovered ? " hovered" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragEnter={e => {
          if (e.dataTransfer.types.includes("application/json")) setIsHovered(true);
        }}
        onDragLeave={() => setIsHovered(false)}
      >
        {/* Controles de fecha */}
        <div className="controls">
          
          <label>
            Fecha inicio:
            <input
              style={{
                marginLeft: "0.2rem"
              }}
              name="start"
              type="date"
              value={formatISO(dataStart, { representation: "date" })}
              max={formatISO(dataEnd, { representation: "date" })}
              onChange={handlePickerChange(setDataStart, true)}
            />
          </label>

          <label style={{ marginLeft: "1rem" }}>
            Fecha fin:
            <input
              style={{
                  marginLeft: "0.2rem"
                }}
              name="end"
              type="date"
              value={formatISO(dataEnd, { representation: "date" })}
              min={formatISO(dataStart, { representation: "date" })}
              onChange={handlePickerChange(setDataEnd, true)}
            />
          </label>
          <button 
          style={{
            marginLeft: "2rem"
          }}
          onClick={() => {
            setViewStart(dataStart);
            setViewEnd(endOfDay(dataEnd));
          }}>
            Resetear Zoom
          </button>
        </div>

        {/* Zona de gráficas */}
        <div className="charts-container">
          <div className="charts-header">
            <p className="dashboard-description">
              Arrastra un field desde el Sidebar para añadir más gráficas
            </p>
            {charts.length === 0 && (
              <p className="dashboard-empty">No hay gráficos en el dashboard.</p>
            )}
          </div>

          {charts.map((chart, idx) => {
            const { data, isFetching, error } = chartQueries[idx] || {};

            const chartConfig = data
              ? {
                  datasets: [
                    {
                      label: chart.field,
                      data: data.map(d => ({ x: new Date(d.time), y: d.value })),
                      borderColor: "black",
                      borderWidth: 2,
                      pointRadius: 0
                    }
                  ]
                }
              : null;

            return (
              <div
                key={idx}
                className="chart-card"
                style={{
                  position: "absolute",
                  transform: `translate(${chart.x}px, ${chart.y}px)`,
                  width: chart.width,
                  height: chart.height,
                  boxSizing: "border-box",
                  overflow: "hidden"
                }}
              >
                {/* Handle de movimiento */}
                <div
                  className="card-handle"
                  onMouseDown={e => handleDragStart(e, idx)}
                  style={{
                    height: 24,
                    display: "flex",
                    alignItems: "center",
                    padding: "0 8px",
                    background: "#f0f0f0",
                    borderBottom: "1px solid #ccc",
                    cursor: "grab",
                    userSelect: "none"
                  }}
                >
                  <span
                    style={{
                      flex: 1,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis"
                    }}
                  >
                    {chart.field}
                  </span>

                  <button
                    className="close-btn"
                    onClick={() => setCharts(prev => prev.filter((_, i) => i !== idx))}
                    style={{ marginLeft: 8 }}
                  >
                    ✕
                  </button>
                </div>

                {/* Canvas y resizer */}
                <div style={{ width: "100%", height: "calc(100% - 24px)" }}>
                  {isFetching && <p style={{ textAlign: "center" }}>Cargando datos…</p>}
                  {error && <p style={{ textAlign: "center" }}>Error: {error.message}</p>}
                  {!isFetching && chartConfig && <Line data={chartConfig} options={chartOptions} />}
                  {!isFetching && !chartConfig && <p style={{ textAlign: "center" }}>Sin datos</p>}

                  <div
                    className="resize-handle"
                    style={{
                      width: 15,
                      height: 15,
                      background: "#333",
                      position: "absolute",
                      bottom: 0,
                      right: 0,
                      cursor: "se-resize"
                    }}
                    onMouseDown={e => handleResizeStart(e, idx)}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
