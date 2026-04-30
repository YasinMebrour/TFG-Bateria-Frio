import React, { useState, useEffect } from 'react';
import SingleDaySlider from '../../components/SingleDaySlider';
import '../../assets/styles/ModoAhorroDiaEditor.css';
import { CalendarPlus, Trash2 } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { useAuth } from '../../context/AuthContext';

const API = '/planificacion';

export default function DiaEditorPruebas() {
  const [savedDays, setSavedDays] = useState([]);
  const api = useApi();
  const { authFetch } = useAuth();
  const [newDay, setNewDay] = useState('');
  const [editingDay, setEditingDay] = useState(null);

  // util rápido para “YYYY-MM-DD”
  const todayISO = new Date().toISOString().slice(0, 10);


  const btnStyle = { padding: '.5rem 1rem', border: 'none', borderRadius: 4, cursor: 'pointer' };

  function timeToMinutes(str) {
    const h = +str.slice(-8, -6), m = +str.slice(-5, -3);
    return h * 60 + m;
  }
  function minutesToTime(m) {
    const h = String(Math.floor(m / 60)).padStart(2, '0');
    const min = String(m % 60).padStart(2, '0');
    return `${h}:${min}:00`;
  }

  // Parseo de schedule de la API a formato frontend
  const parseSchedule = (api) =>
    (api.schedule || []).map(i => ({
      start: i.inicio_ahorro?.slice(11, 16) ? timeToMinutes(i.inicio_ahorro) : null,
      end: i.final_ahorro?.slice(11, 16) ? timeToMinutes(i.final_ahorro) : null,
    })).filter(iv => iv.start !== null && iv.end !== null);

  // Carga inicial y tras guardar
  const loadDays = () => {
    authFetch(`http://localhost:8000${API}/lista`)
      .then(res => {
        if (!res.ok) throw new Error(`GET ${API}/lista → ${res.status}`);
        return res.json();
      })
      .then(data =>
        setSavedDays(
          data.map(d => ({
            date: d.fecha,
            intervals: parseSchedule(d),
            modoAhorro: d.modo_ahorro,
          }))
        )
      )
      .catch(() => {});
  };

  useEffect(() => {
    loadDays();
  }, []);

  const addDay = () => {
    if (!newDay || savedDays.some(e => e.date === newDay)) return;
    setSavedDays([
      ...savedDays,
      { date: newDay, intervals: [], modoAhorro: false }
    ]);
    setEditingDay(newDay);
    setNewDay('');
  };

  const delDay = (date) => {
    setSavedDays(savedDays.filter(e => e.date !== date));
    if (editingDay === date) setEditingDay(null);
  };

  const updateIntervals = (date, intervals) => {
    setSavedDays(list =>
      list.map(d =>
        d.date === date ? { ...d, intervals } : d
      )
    );
  };

  const updateModoAhorro = (date, modoAhorro) => {
    setSavedDays(list =>
      list.map(d =>
        d.date === date
          ? {
              ...d,
              modoAhorro,
              intervals: modoAhorro ? d.intervals : [],
            }
          : d
      )
    );
  };

  const saveAllDays = async () => {
    const payload = savedDays.map(d => ({
      fecha: d.date,
      modo_ahorro: d.modoAhorro,
      intervalos: d.modoAhorro
        ? d.intervals.map(({ start, end }) => ({
            hora_inicio: minutesToTime(start),
            hora_fin: minutesToTime(end),
          }))
        : [],
    }));
    await api.post(`${API}/dias`, payload);
    // Recarga de la lista real tras guardar
    loadDays();
  };

  const setIntervalsAndMode = (date, newIntervals) => {
    updateIntervals(date, newIntervals);                // ya tenías esta
    updateModoAhorro(date, newIntervals.length > 0);    // activa / desactiva
  };

  return (
    <div>
      {/* Paneles en fila */}
      <div style={{ display: 'flex', gap: '2rem', padding: '1rem' }}>
        {/* Panel izquierdo */}
        <div className="tc-fest-panel">
          <h2 className="tc-fest-title">Días Modo Ahorro</h2>
          <div className="tc-fest-inputs">
            <input
              type="date"
              value={newDay}
              onChange={e => setNewDay(e.target.value)}
              min={todayISO}
            />
            <button onClick={addDay} className="tc-btn-add">+</button>
          </div>
          <ul className="tc-fest-list">
            {savedDays.length > 0 ? savedDays.map(e => (
              <li
                key={e.date}
                onClick={() => setEditingDay(e.date)}
                className={e.date === editingDay ? 'activo' : ''}
              >
                <span>{e.date}</span>
                <button
                  className="tc-btn-danger"
                  onClick={evt => { evt.stopPropagation(); delDay(e.date); }}
                  aria-label={`Eliminar ${e.date}`}
                >
                  <Trash2 size={16} />
                </button>
              </li>
            )) : (
              <li className="sin-dias">Sin días</li>
            )}
          </ul>
        </div>

        {/* Zona derecha: editor */}
        <div style={{
          flex: 3,
          border: '1px solid #ccc',
          borderRadius: 8,
          padding: '1rem',
          background: '#f8f9fa'
        }}>
          {editingDay ? (
            <>
              <h3 style={{ marginTop: 20, textAlign: 'center' }}>{editingDay}</h3>
              <div className="config-row" style={{ marginBottom: '2rem' }}>
                <div style={{ width: 160, fontWeight: 600, padding: '0.75rem' }}>Planificación</div>
                <SingleDaySlider
                  intervals={
                    savedDays.find(e => e.date === editingDay)?.intervals || []
                  }
                  onChange={newIntervals => setIntervalsAndMode(editingDay, newIntervals)}
                />
              </div>
              <div className="config-row" style={{ textAlign: 'center', marginBottom: '2rem' }}>
                <button
                  type="button"
                  className={`btn-toggle ${
                    savedDays.find(e => e.date === editingDay)?.modoAhorro ? 'active' : 'inactive'
                  }`}
                  onClick={() => {
                    const actual = savedDays.find(e => e.date === editingDay)?.modoAhorro;
                    updateModoAhorro(editingDay, !actual);
                  }}
                  style={{
                    ...btnStyle,
                    background: savedDays.find(e => e.date === editingDay)?.modoAhorro
                      ? '#198754'
                      : '#dc3545',
                    color: '#fff',
                    minWidth: 220,
                  }}
                >
                  Modo Ahorro:{' '}
                  {savedDays.find(e => e.date === editingDay)?.modoAhorro ? 'Sí' : 'No'}
                </button>
              </div>
            </>
          ) : (
            <div style={{ color: '#666', textAlign: 'center', marginTop: '2rem' }}>
              Selecciona un día a editar
            </div>
          )}
        </div>
      </div>
      {/* Botón guardar todos los días: en una fila nueva y centrado, ocupa 70% */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginTop: '0.0rem',
        marginBottom: '1.5rem'
      }}>
        <div style={{ width: '100%', textAlign: 'right' }}>
          <button
            onClick={saveAllDays}
            style={{
              ...btnStyle,
              width: '100%',
              background: '#0d6efd',
              color: '#fff'
            }}
          >
            Guardar planificación diaria
          </button>
        </div>
      </div>
    </div>
  );
}
