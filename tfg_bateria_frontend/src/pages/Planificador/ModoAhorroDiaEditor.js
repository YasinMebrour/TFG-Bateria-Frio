// ===============================
// File: src/pages/ModoAhorroDiaEditor.jsx
// ===============================
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import SingleDaySlider from '../../components/SingleDaySlider';
import { useApi } from '../../hooks/useApi';

const days =[
    "LUNES", "MARTES", "MIERCOLES",
  "JUEVES", "VIERNES", "SABADO", "DOMINGO",
]

const DIAS_VACIO = Object.fromEntries(days.map(d => [d, []]));

const btnStyle = {
  padding: '0.45rem 1.1rem',
  borderRadius: 6,
  border: 'none',
  fontWeight: 600,
  cursor: 'pointer',
};

const minutes = t => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
const mmToTime = m => `${String(Math.floor(m / 60)).padStart(2,'0')}:${String(m % 60).padStart(2,'0')}:00`;

const dayNameFromDate = date => {
  const mapping = ['DOMINGO','LUNES','MARTES','MIERCOLES','JUEVES','VIERNES','SABADO'];
  return mapping[date.getDay()];
};
const formatDate = date => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;

export default function ModoAhorroDiaEditor({ isEditor, editingDay: editingDayProp, proposedByDay }) {
  // Estado de planificación manual y óptima
  const [manualData, setManualData] = useState(() => (
    proposedByDay ? { ...DIAS_VACIO, ...proposedByDay } : { ...DIAS_VACIO }
  ));
  const [optimoData, setOptimoData] = useState({ ...DIAS_VACIO });

  // Modo activo y día editado
  const [modoSeleccionado, setModoSeleccionado] = useState('manual');
  const [editingDay, setEditingDay] = useState(editingDayProp || 'LUNES');
  const [draft, setDraft] = useState([]);
  const [modoAhorroActivo, setModoAhorroActivo] = useState(true);
  const api = useApi();

  // Clipboard y panel de pegado
  const [clipboard, setClipboard] = useState(null);
  const [selectDaysVisible, setSelectDaysVisible] = useState(false);
  const [targetDays, setTargetDays] = useState([]);

  // Fechas de hoy y mañana
  const { todayDate, tomorrowDate, todayName, tomorrowName } = useMemo(() => {
    const todayDate = new Date();
    const tomorrowDate = new Date(todayDate.getTime() + 864e5);
    const todayName = dayNameFromDate(todayDate);
    const tomorrowName = dayNameFromDate(tomorrowDate);
    return { todayDate, tomorrowDate, todayName, tomorrowName };
  }, []);

  // Planificación real sólo para mostrar (readonly)
  const [actualData, setActualData] = useState(DIAS_VACIO);

  // Cargar planificación real (solo lectura)
  const fetchWeekPlan = useCallback(async () => {
    try {
      const raw = await api.get('/planificacion/semana');
      const mapped = {};
      days.forEach(d => {
        mapped[d] = (raw[d] || []).map(i => ({
          start: minutes(i.hora_inicio),
          end: minutes(i.hora_fin),
          modo_ahorro: i.modo_ahorro,
        }));
      });
      setActualData(mapped);
    } catch (e) {
      setActualData(DIAS_VACIO);
    }
  }, []);

  useEffect(() => { fetchWeekPlan(); }, [fetchWeekPlan]);

  // Sincronizar draft y modoAhorroActivo según modo y día activo
  useEffect(() => {
    if (modoSeleccionado === 'manual') {
      const entry = manualData[editingDay] || [];
      setDraft(entry);
      setModoAhorroActivo(entry.length > 0);
    } else {
      const entry = optimoData[editingDay] || [];
      setDraft(entry);
      setModoAhorroActivo(entry.length > 0);
    }
  }, [modoSeleccionado, editingDay, manualData, optimoData]);

  useEffect(() => {
  if (modoSeleccionado !== 'manual') return;

  let actualizado = false;
  const nuevaManualData = { ...manualData };

  days.forEach(d => {
    const hayPropuesta = proposedByDay && proposedByDay[d] && proposedByDay[d].length > 0;
    const manualVacio = !manualData[d] || manualData[d].length === 0;
    const actualHay = actualData[d] && actualData[d].length > 0;

    // Solo copia si:
    //  - El día está vacío en manualData
    //  - NO hay propuesta para ese día
    //  - Hay datos reales para ese día
    if (manualVacio && !hayPropuesta && actualHay) {
      nuevaManualData[d] = actualData[d].map(iv => ({ ...iv }));
      actualizado = true;
    }
  });

  if (actualizado) setManualData(nuevaManualData);
  // eslint-disable-next-line
}, [modoSeleccionado, actualData, proposedByDay]);


  // Cambia el draft y el estado adecuado
  const onDraftChange = (newIv) => {
    setDraft(newIv);
    if (modoSeleccionado === 'manual') {
      setManualData(prev => ({ ...prev, [editingDay]: newIv }));
    } else {
      setOptimoData(prev => ({ ...prev, [editingDay]: newIv }));
    }
  };

  // Alternar modo ahorro
  const onToggleAhorro = () => {
    const activo = !modoAhorroActivo;
    setModoAhorroActivo(activo);
    if (modoSeleccionado === 'manual') {
      if (!activo) {
        setDraft([]);
        setManualData(prev => ({ ...prev, [editingDay]: [] }));
      }
    } else {
      if (!activo) {
        setDraft([]);
        setOptimoData(prev => ({ ...prev, [editingDay]: [] }));
      }
    }
  };

  // Guardar toda la semana (manual)
  // Guardar toda la semana (manual, origen Gemelo)
const handleSaveSemana = async () => {
  const dias = days.map((d) => {
    const ivs = manualData[d];
    return {
      day_name: d,
      modo_ahorro: ivs.length > 0,
      intervalos: ivs.map((it) => ({
        hora_inicio: mmToTime(it.start),
        hora_fin: mmToTime(it.end),
        modo_ahorro: it.modo_ahorro,
      })),
    };
  });
  const weekPayload = {
    modo_planif: "Gemelo",  // Aquí indicas el origen manual
    dias,
  };
  try {
    await api.post('/planificacion/semana', weekPayload);
    await fetchWeekPlan();
    setClipboard(null);
  } catch {}
};


  // Guardar sólo hoy optimizado
  async function handleSaveDiaOptimo() {
    const ivs = optimoData[todayName] ?? [];
    const diaPayload = {
      fecha: formatDate(todayDate),
      modo_ahorro: ivs.length > 0,
      intervalos: ivs.map(it => ({
        hora_inicio: mmToTime(it.start),
        hora_fin: mmToTime(it.end),
        modo_ahorro: it.modo_ahorro,
      })),
    };

    try {

      // 2) Activa el modo Optimizado para la semana
      await api.post('/planificacion/semana', {
        modo_planif: "Optimizado",
        dias: [],
      });

      await fetchWeekPlan();     // refresca el panel
      setClipboard(null);
    } catch (err) {
      console.error(err);
    }
  }


  // Fetch solo para modo óptimo
  const fetchOptimizedDate = async (date) => {
    const fechaStr = formatDate(date);
    try {
      const raw = await api.get(
        `/planificacion/optimizada?start_date=${fechaStr}`
      );
      const intervals = (raw.schedule || []).map(i => ({
        start: minutes(i.inicio_ahorro.slice(11, 16)),
        end: minutes(i.final_ahorro.slice(11, 16)),
      }));
      const dayName = dayNameFromDate(date);
      if (days.includes(dayName)) {
        setOptimoData(prev => ({ ...prev, [dayName]: intervals }));
      }
    } catch {}
  };

  useEffect(() => {
    if (modoSeleccionado === 'optimo') {
      fetchOptimizedDate(todayDate);
      fetchOptimizedDate(tomorrowDate);
    }
  }, [modoSeleccionado, todayDate, tomorrowDate]);

  // Copiar, pegar (manual solo)
  const copyAndSelect = () => {
    setClipboard([...manualData[editingDay]]);
    setTargetDays([]);
    setSelectDaysVisible(true);
  };

  const pasteToDays = () => {
    if (clipboard === null || targetDays.length === 0) {
      setSelectDaysVisible(false);
      return;
    }
    setManualData((prev) => {
      const updated = { ...prev };
      targetDays.forEach((d) => {
        updated[d] = clipboard.map((it) => ({ ...it }));
      });
      return updated;
    });
    setSelectDaysVisible(false);
  };

  const toggleTargetDay = (day) => {
    setTargetDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  return (
    <div className="dia-editor">
      {/* Selector de modo */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
        <button
          onClick={() => setModoSeleccionado('manual')}
          style={{
            ...btnStyle,
            background: modoSeleccionado === 'manual' ? '#198754' : '#adb5bd',
            color: '#fff',
            minWidth: 180,
          }}
          disabled={!isEditor}
        >
          Modo Ahorro Manual
        </button>
        <button
          onClick={() => setModoSeleccionado('optimo')}
          style={{
            ...btnStyle,
            background: modoSeleccionado === 'optimo' ? '#198754' : '#adb5bd',
            color: '#fff',
            minWidth: 180,
          }}
          disabled={!isEditor}
        >
          Modo Ahorro Optimizado
        </button>
      </div>

      <div
        style={{
          border: '1px solid #ccc',
          borderRadius: 8,
          padding: '1.25rem',
          background: '#f8f9fa',
        }}
      >
        {/* ---------- MANUAL ---------- */}
        {modoSeleccionado === 'manual' && (
          <>
            {/* Selector días */}
            <div style={{ display: 'flex', gap: '.5rem', marginBottom: '2.75rem' }}>
              {days.map((d) => {
                const active = d === editingDay;
                const has = actualData[d]?.length > 0;
                return (
                  <button
                    key={d}
                    onClick={() => isEditor && setEditingDay(d)}
                    disabled={!isEditor}
                    style={{
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center', 
                      padding: '.55rem 0',
                      borderRadius: 6,
                      border: active ? '3px solid #0a58ca' : '1px solid #adb5bd',
                      background: active ? '#0d6efd' : has ? '#e7f1ff' : '#fff',
                      color: active ? '#fff' : '#000',
                      fontWeight: 600,
                    }}
                  >
                    {d}
                  </button>
                );
              })}
            </div>

            {/* Actual readonly */}
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.75rem' }}
            >
              <div style={{ width: 160, fontWeight: 600 }}>Planificación actual</div>
              <div style={{ flex: 1 }}>
                <SingleDaySlider
                  key={'actual' + editingDay}
                  intervals={actualData[editingDay] || []}
                  onChange={() => {}}
                  disabled
                />
              </div>
            </div>

            {/* Editable */}
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.75rem' }}
            >
              <div style={{ width: 160, fontWeight: 600 }}>Planificación nueva</div>
              <div style={{ flex: 1 }}>
                <SingleDaySlider
                  key={'nueva' + editingDay}
                  intervals={draft}
                  onChange={onDraftChange}
                  disabled={!isEditor}
                />
              </div>
            </div>

            {/* Panel de pegado */}
            {selectDaysVisible && (
              <div
                style={{
                  display: 'flex',
                  gap: '.75rem',
                  marginBottom: '2rem',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  border: '1px solid #adb5bd',
                  borderRadius: 6,
                  padding: '0.8rem',
                  background: '#fff',
                }}
              >
                <span style={{ fontWeight: 600, marginRight: '0.5rem' }}>Pegar en:</span>
                {days.map((d) => (
                  <label key={d} style={{ display: 'flex', alignItems: 'center', gap: '.25rem' }}>
                    <input
                      type="checkbox"
                      checked={targetDays.includes(d)}
                      onChange={() => toggleTargetDay(d)}
                    />
                    {d}
                  </label>
                ))}
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '.75rem' }}>
                  <button
                    onClick={pasteToDays}
                    style={{ ...btnStyle, background: '#198754', color: '#fff' }}
                  >
                    Aplicar
                  </button>
                  <button
                    onClick={() => setSelectDaysVisible(false)}
                    style={{ ...btnStyle, background: '#dc3545', color: '#fff' }}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}

            {/* Interruptor Modo Ahorro */}
            <div className="config-row" style={{ textAlign: 'center', marginBottom: '2rem' }}>
              <button
                type="button"
                className={`btn-toggle ${modoAhorroActivo ? 'active' : 'inactive'}`}
                onClick={onToggleAhorro}
                disabled={!isEditor}
                style={{
                  ...btnStyle,
                  background: modoAhorroActivo ? '#198754' : '#dc3545',
                  color: '#fff',
                  minWidth: 220,
                  opacity: isEditor ? 1 : 0.5,
                }}
              >
                Modo Ahorro: {modoAhorroActivo ? 'Sí' : 'No'}
              </button>
            </div>

            {/* Botones copiar y guardar */}
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button
                onClick={copyAndSelect}
                disabled={!isEditor}
                style={{
                  ...btnStyle,
                  background: '#6c757d',
                  color: '#fff',
                  opacity: isEditor ? 1 : 0.5,
                }}
              >
                Copiar
              </button>
              <button
                onClick={handleSaveSemana}
                style={{ ...btnStyle, background: '#0d6efd', color: '#fff' }}
              >
                Guardar y Establecer Planificación Semanal
              </button>
            </div>
          </>
        )}

        {/* ---------- OPTIMO ---------- */}
        {modoSeleccionado === 'optimo' && (
          <>
            {days.map((d) => {
              const isToday = d === todayName;
              const isTomorrow = d === tomorrowName;
              const hasIntervals = (optimoData[d] && optimoData[d].length > 0);
              return (
                <div
                  key={d}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    marginBottom: '0.5rem',
                    marginTop: (isToday || isTomorrow) && hasIntervals ? '2rem' : undefined
                  }}
                >
                  <div style={{ width: 160, fontWeight: 600 }}>
                    {isToday
                      ? `${d} (Hoy)`
                      : isTomorrow
                        ? `${d} (Mañana)`
                        : d}
                  </div>
                  <div style={{ flex: 1 }}>
                    {(isToday || isTomorrow) && hasIntervals ? (
                      <SingleDaySlider
                        intervals={optimoData[d] || []}
                        onChange={() => {}}
                        disabled
                      />
                    ) : (
                      <div style={{ fontStyle: 'italic', color: '#666', padding: '0.5rem 0' }}>
                        Por definir
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div style={{ textAlign: 'right', marginTop: '1rem' }}>
              <button
                onClick={handleSaveDiaOptimo}
                style={{ ...btnStyle, background: '#0d6efd', color: '#fff' }}
              >
                Guardar y Establecer Plan Optimizado
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
