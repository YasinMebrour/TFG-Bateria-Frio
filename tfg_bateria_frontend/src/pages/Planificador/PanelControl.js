import { useState, useEffect } from "react";
import "../../assets/styles/Panel_control.css";
import { useApi } from "../../hooks/useApi";
import { useAuth } from "../../context/AuthContext";
import { API_URL } from "../../config/apiConfig";

const WS_URL = API_URL.replace(/^http/, "ws") + "/wsplanificacion/ws/planificacion";

const DAY_LABELS = [
  "LUNES", "MARTES", "MIERCOLES",
  "JUEVES", "VIERNES", "SABADO", "DOMINGO",
];

// Parser robusto: siempre 6 valores para cada día de la semana
function parseSchedule(dias) {
  const obj = {};
  for (const d of DAY_LABELS) obj[d] = [0, 0, 0, 0, 0, 0]; // Inicializa todo a ceros
  for (const [k, v] of Object.entries(dias)) {
    const up = k.toUpperCase();
    if (DAY_LABELS.includes(up)) {
      obj[up] = v.flat().map(h =>
        h === "0" ? 0 : Number(h.split(":")[0])
      );
      while (obj[up].length < 6) obj[up].push(0);
    }
  }
  return obj;
}

export default function PanelControl({ className = "" }) {
  const [schedule, setSchedule] = useState(() =>
    DAY_LABELS.reduce((a, d) => ({ ...a, [d]: [0, 0, 0, 0, 0, 0] }), {})
  );
  const [segTemp, setSegTemp] = useState(0);
  const [segHum, setSegHum] = useState(0);
  const [enabled, setEnabled] = useState(false);
  const [modo, setModo] = useState("Optimizado");
  const [now, setNow] = useState(new Date());
  const api = useApi();
  const { token } = useAuth();

  // 1. función fetch reutilizable
  // -------------------------------
// Versión robusta de la función
// -------------------------------
  async function fetchPlanificacionActual() {
    try {
      const res = await api.get("/planificacion/panel_control");
      const panel = res;

      // 2) usarlo
      setSegTemp(panel.banda_seguridad_temperatura ?? 0);
      setSegHum(panel.banda_seguridad_humedad ?? 0);
      setEnabled(Boolean(panel.modo_ahorro_activo));

      // normaliza a minúsculas y sin espacios
      setModo((panel.origen ?? "Optimizado").trim());

      setSchedule(parseSchedule(panel.dias));
    } catch (err) {
      console.error("Error obteniendo planificación:", err);
    }
  }


  // 2. Llama a fetch al montar el componente
  useEffect(() => {
    fetchPlanificacionActual();
  }, []);

  // 3. Conecta WebSocket
  useEffect(() => {
    if (!token) return;
    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
    ws.onmessage = (event) => {
      if (event.data === 'planificacion_actualizada') {
        console.log("Websocket panel control")
        fetchPlanificacionActual();
      }
    };
    return () => ws.close();
  }, [token]);

  // 4. reloj (igual que antes)
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const dd = n => n.toString().padStart(2, "0");

  // Solo lectura
  return (
    <div className={`panel ${className}`}>
      <div className="header-row">
        <span className="code">C3-40</span>
        <span className="title">AHORRO&nbsp;ENERGÉTICO</span>
      </div>
      <div className="datetime">
        {dd(now.getDate())}/{dd(now.getMonth() + 1)}/{now.getFullYear().toString().slice(-2)}&nbsp;
        ({now.toLocaleDateString("es-ES", { weekday: "short" }).toUpperCase()})&nbsp;
        {dd(now.getHours())}:{dd(now.getMinutes())}
      </div>
      <table className="schedule">
        <thead>
          <tr>
            <th></th>
            <th>Inicio</th>
            <th>Fin</th>
            <th>Inicio</th>
            <th>Fin</th>
            <th>Inicio</th>
            <th>Fin</th>
          </tr>
        </thead>
        <tbody>
          {DAY_LABELS.map((d) => (
            <tr key={d}>
              <td className="day">{d}</td>
              {(schedule[d] ?? [0,0,0,0,0,0]).map((v, idx) => (
                <td className={`cell c${idx}`} key={idx}>
                  <div className="cell-value">{v}</div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="params">
        <div className="row">
          <span className="label">BANDA&nbsp;SEGUR.TEMPERATURA</span>
          <div className="cell-value-down">{segTemp}</div>
          <span className="unit">°C</span>
        </div>
        <div className="row">
          <span className="label">BANDA&nbsp;SEGURIDAD&nbsp;HUMEDAD</span>
          <div className="cell-value-down">{segHum}</div>
          <span className="unit">%</span>
        </div>
        <div className="row">
          <span className="label">AHORRO&nbsp;ENERGÍA&nbsp;HABILITADO</span>
          <button className={`toggle ${enabled ? "on" : "off"}`} disabled>
            {enabled ? "SI" : "NO"}
          </button>
        </div>
        <div className="row">
          <span className="label">PLANIFICACIÓN</span>
          <div className="button-group">
            <button className={`modo optimizado ${modo === "Optimizado" ? "activo" : ""}`} disabled>
              Optimizado
            </button>
            <button className={`modo manual-camara ${modo === "Camara" ? "activo" : ""}`} disabled>
              Cámara
            </button>
            <button className={`modo manual-gemelo ${modo === "Gemelo" ? "activo" : ""}`} disabled>
              Gemelo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
