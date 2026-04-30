// ===============================
// File: src/pages/ConfiguracionPage.jsx
// ===============================
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import styles from '../../assets/styles/Config.module.css';
import { useLocation, useNavigate } from 'react-router-dom';
import ModoAhorroDiaEditor from './ModoAhorroDiaEditor';
import DiaEditor from './DiaEditor';
import { useAuth } from '../../context/AuthContext';
import PanelControl from './PanelControl';

/* ─── helpers ─── */
// YYYY-MM-DD en zona local
const ymdLocal = d =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const days = [
    "LUNES", "MARTES", "MIERCOLES",
  "JUEVES", "VIERNES", "SABADO", "DOMINGO",
]

const DIAS_VACIO = Object.fromEntries(days.map(d => [d, []]));
const minutes = t => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
const mmToTime = m => `${String(Math.floor(m / 60)).padStart(2,'0')}:${String(m % 60).padStart(2,'0')}`;

// Devuelve lunes local de la fecha dada
const getMonday = (d = new Date()) => {
  const x = new Date(d), g = x.getDay();
  x.setDate(x.getDate() + ((g === 0 ? -6 : 1) - g));
  x.setHours(0, 0, 0, 0);
  return x;
};
const addDays = (b, n) => { const dd = new Date(b); dd.setDate(dd.getDate() + n); return dd; };
const rangoSemana = mon => {
  const fmt = { day: '2-digit', month: 'short' };
  return `${mon.toLocaleDateString('es-ES', fmt)} – ${addDays(mon, 6).toLocaleDateString('es-ES', fmt)}`;
};
const TODAY_MONDAY = getMonday();
/* ───────────────────────────── */

export default function Planificador() {
  const { authFetch } = useAuth();
  const navigate      = useNavigate();
  const { state }     = useLocation();
  const selectedPlan  = state?.selectedPlan;
  const proposedConst = state?.proposedSchedulerData || {};

  /* -------- estado “semana” -------- */
  const initialMonday   = state?.weekStart ? new Date(state.weekStart) : TODAY_MONDAY;
  const [weekOffset, setWeekOffset] = useState(
    Math.round((initialMonday - TODAY_MONDAY) / (7 * 864e5))
  );

  const [editingDay, setEditingDay] = useState(state?.editingDay || 'LUNES');
  const [clipboard,  setClipboard]  = useState(null);

  // weekData almacena un objeto { "Lunes": [...], "Martes": [...], ... }
  const [weekData,   setWeekData]   = useState(DIAS_VACIO);

  /* -------- helpers derivados -------- */
  const weekStartDate = useMemo(() => addDays(TODAY_MONDAY, weekOffset * 7), [weekOffset]);
  const weekLabel     = useMemo(() => rangoSemana(weekStartDate), [weekStartDate]);
  const isPastWeek    = weekStartDate < TODAY_MONDAY;

  // proposedByDay se puede usar si existe scheduling propuesto
  // mapea { "YYYY-MM-DD": { "Lunes": [...], ... } } → tomamos la ISO de weekStart
  const weekKeyISO    = ymdLocal(weekStartDate);
  const proposedByDay = proposedConst[weekKeyISO] || DIAS_VACIO;

  /* =====================
     1. Wrapper GET /planificacion/semana
     ===================== */
  const fetchWeekPlan = useCallback(async () => {
    // Ahora GET /planificacion/semana sin query param
    const res = await authFetch(`http://localhost:8000/planificacion/semana`);
    if (!res.ok) throw new Error(`GET /planificacion/semana → ${res.status}`);
    const raw = await res.json();
    // raw será un objeto { "Lunes": [{hora_inicio, hora_fin, modo_ahorro}, ...], ... }
    const mapped = { ...DIAS_VACIO };
    days.forEach(d => {
      mapped[d] = (raw[d] || []).map(i => ({
        start: minutes(i.hora_inicio ?? i.start_time),
        end:   minutes(i.hora_fin   ?? i.end_time),
      }));
    });
    return mapped;
  }, [authFetch]);

  /* =====================
     2. Cargar semana visible
     ===================== */
  const loadWeek = useCallback(() => {
    (async () => {
      try {
        const mapped = await fetchWeekPlan();
        setWeekData(mapped);
      } catch (e) {
        console.error('loadWeek', e);
        setWeekData(DIAS_VACIO);
      }
    })();
  }, [fetchWeekPlan]);

  useEffect(() => {
    loadWeek();
  }, [loadWeek]);




  /* =====================
     3. Persistencia (POST /planificacion/semana)
     ===================== */
  const persistSemana = async (weekPayload) => {
    // weekPayload debe ser un array de 7 objetos { day_name, modo_ahorro, intervalos: [ { hora_inicio, hora_fin, modo_ahorro } ] }
    const res = await authFetch('http://localhost:8000/planificacion/semana', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify(weekPayload),
    });
    if (!res.ok) {
      console.error('Error al guardar semana:', res.status);
      throw new Error(`POST /planificacion/semana → ${res.status}`);
    }
  };

  /* =====================
     4. Helpers auxiliares para pasar a ModoAhorroDiaEditor
     ===================== */
  const setIntervalsByDay = updater => 
    setWeekData(prev => (typeof updater === 'function' ? updater(prev) : updater));

  const applyFuture = (dayName, newIntervals, modoAhorro) => {
    // Actualizamos en memoria weekData[dayName], pero no guardamos de inmediato.
    setIntervalsByDay(prev => ({
      ...prev,
      [dayName]: newIntervals,
    }));
  };

  /* =====================
     5. Cuando el usuario finalmente pulsa “Guardar” en ModoAhorroDiaEditor,
        recibe internamente el array completo y llama a persistSemana
     ===================== */
  const handleGuardarSemana = async () => {
    try {
      // Construimos el array de 7 días a enviar:
      const payload = days.map(d => {
        const ivs = weekData[d] || [];
        const modo = ivs.length > 0; // si hay intervalos, consideramos modo_ahorro=true
        return {
          day_name:    d,
          modo_ahorro: modo,
          intervalos:  ivs.map(itv => ({
            hora_inicio: mmToTime(itv.start),
            hora_fin:    mmToTime(itv.end),
            modo_ahorro: modo,
          })),
        };
      });
      await persistSemana(payload);
      // Recargar para asegurar consistencia
      await loadWeek();
    } catch (err) {
      console.error(err);
      alert('Hubo un error guardando la semana.');
    }
  };

  /* =====================
     6. Render
     ===================== */
  const [activeTab, setActiveTab] = useState("semana"); // o "dia"

  return (
    <div className={styles.demo}>
      <div style={{ flex: 1 }}>
        <div className={styles.tab}>
          <div className={styles['tab-wrapper']}>

            {/* --------- Tabs --------- */}
            <input
              id="tab1"
              type="radio"
              name="tabsA"
              checked={activeTab === "semana"}
              onChange={() => setActiveTab("semana")}
            />
            <label htmlFor="tab1">Semana</label>

            <input
              id="tab2"
              type="radio"
              name="tabsA"
              checked={activeTab === "dia"}
              onChange={() => setActiveTab("dia")}
            />
            <label htmlFor="tab2">Día</label>

            {/* --------- Tab contents --------- */}
            <div className={styles['tab-content']} style={{ display: activeTab === "semana" ? "block" : "none" }}>
              <div className={styles.row}>
                <ModoAhorroDiaEditor
                  editingDay={editingDay}
                  isEditor={true}
                  proposedByDay={proposedByDay}
                />
                <PanelControl className="side-panel" />
              </div>
            </div>
            <div className={styles['tab-content']} style={{ display: activeTab === "dia" ? "block" : "none" }}>
              <div className={styles.row}>
                <DiaEditor />
                <PanelControl className="side-panel" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
