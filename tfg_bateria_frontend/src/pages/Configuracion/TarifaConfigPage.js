import React, { useEffect, useState } from 'react';
import '../../assets/styles/Tarifa.css';
import { CalendarPlus, Trash2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';


const MONTHS = [
  'Enero','Febrero','Marzo','Abril','Mayo','Junio',
  'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
];
const HOURS = Array.from({ length: 24 }, (_, i) => `${i}:00 - ${i + 1}:00`);
const TARIFFS = [
  { id: 'P1', color: '#ff0000' },
  { id: 'P2', color: '#ffeb00' },
  { id: 'P3', color: '#0070bf' },
  { id: 'P4', color: '#ff00ff' },
  { id: 'P5', color: '#ff9900' },
  { id: 'P6', color: '#00af50' }
];
const TARIFF_IDS = TARIFFS.map(t => t.id);
const defaultGrid = () => Array.from({ length: 24 }, () => Array.from({ length: 13 }, () => 'P6'));
const tariffColor = id => TARIFFS.find(t => t.id === id)?.color ?? '#ccc';

export default function TarifaConfigPage() {
  const { authFetch } = useAuth();
  const [grid, setGrid] = useState(defaultGrid());
  const [festivos, setFest] = useState([]);
  const [newFest, setNewFest] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [peajes, setPeajes] = useState(
    TARIFF_IDS.map(id => ({ nombre: id, peaje: 0 }))
  );

  const toPct = v => (v ?? 0) * 100;      
  const toFrac = v => (v ?? 0) / 100; 

  useEffect(() => {
    async function loadCfg() {
      try {
        const res = await authFetch('http://localhost:8000/tarifas');
        if (!res.ok) {
          console.error('Error HTTP al cargar tarifas y festivos:', res.status);
          return;
        }
        const { tarifas, festivos, peajes } = await res.json();

        const g = defaultGrid();
        tarifas.forEach(({ month, day_type, hour, tarifa }) => {
          const col = day_type === 'weekday' ? (month ?? 1) - 1 : 12;
          g[hour][col] = tarifa;
        });

        setGrid(g);
        setFest(festivos);
        setPeajes(
          TARIFF_IDS.map(id => {
            const encontrado = (peajes ?? []).find(p => p.nombre === id);
            return { nombre: id, peaje: encontrado?.peaje ?? 0 };
          })
        );
      } catch (e) {
        console.error('Error cargando configuración:', e);
      } finally {
        setLoading(false);
      }
    }
    loadCfg();
  }, []);

  const updateTariff = (h, c, v) =>
    setGrid(prev => prev.map((row, i) =>
      i === h ? row.map((cel, j) => j === c ? v : cel) : row
    ));

  const addFestivo = () => {
    if (newFest && !festivos.includes(newFest)) {
      setFest([...festivos, newFest]);
      setNewFest('');
    }
  };

  const delFestivo = d => setFest(festivos.filter(f => f !== d));

  const handlePeajeValueChange = (nombre, frac) => {
    const nuevos = peajes.map(p =>
      p.nombre === nombre ? { ...p, peaje: isNaN(frac) ? 0 : frac } : p
    );
    setPeajes(nuevos);
  };


  const saveAll = async () => {
    setSaving(true);

    const bloques = [];
    grid.forEach((row, h) =>
      row.forEach((t, c) => {
        if (c < 12) {
          bloques.push({ month: c + 1, day_type: 'weekday', hour: h, tarifa: t });
        } else {
          ['weekend', 'holiday'].forEach((dt) =>
            bloques.push({ month: null, day_type: dt, hour: h, tarifa: t })
          );
        }
      })
    );

    const payload = {
      tarifas: bloques,
      festivos,
      peajes
    };

    try {
      const res = await authFetch('http://localhost:8000/tarifas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        console.error('Error al guardar configuración:', res.status, await res.text());
        alert('Error guardando la configuración');
      }
    } catch (e) {
      console.error('Excepción al guardar:', e);
      alert('Error al guardar la configuración');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="tc-loading">Cargando…</div>;

  const Cell = ({ value, onChange }) => (
    <select
      className={`tc-select tc-${value}`}
      value={value}
      onChange={e => onChange(e.target.value)}
    >
      {TARIFFS.map(t => (
        <option key={t.id} value={t.id} style={{ backgroundColor: t.color }}>
          {t.id}
        </option>
      ))}
    </select>
  );

  return (
    <div className="tc-wrapper">
      {/* ----- Contenedor horizontal: tabla y festivos ----- */}
      <div className="tc-top-row">
        <div className="tc-table-container">
          <table className="tc-table">
            <thead>
              <tr>
                <th>Hora</th>
                {MONTHS.map(m => <th key={m}>{m}</th>)}
                <th>Sáb/Dom<br />Festivos</th>
              </tr>
            </thead>
            <tbody>
              {grid.map((row, h) => (
                <tr key={h}>
                  <td className="tc-hour">{HOURS[h]}</td>
                  {row.map((t, c) => (
                    <td key={c}><Cell value={t} onChange={v => updateTariff(h, c, v)} /></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div> 
  
        <div className="tc-fest-panel">
          <h2 className="tc-fest-title"><CalendarPlus size={16} /> Festivos extra</h2>
          <div className="tc-fest-inputs">
            <input type="date" value={newFest} onChange={e => setNewFest(e.target.value)} />
            <button className="tc-btn" onClick={addFestivo}>+</button>
          </div>
          <ul className="tc-fest-list">
            {festivos.map(d => (
              <li key={d}>
                <span>{d}</span>
                <button className="tc-btn-danger" onClick={() => delFestivo(d)}><Trash2 size={12} /></button>
              </li>
            ))}
            {festivos.length === 0 && <li className="italic text-gray-500">Sin festivos</li>}
          </ul>
        </div>
      </div>
  
      {/* ----- Panel de peajes debajo ----- */}
      <div className="tc-peajes-panel">
        <div className="tc-peajes-row">
          <table className="tc-peajes-table">
            <thead>
              <tr>
                {TARIFF_IDS.map(id => <th key={id}>{id}</th>)}
              </tr>
            </thead>
            <tbody>
            <tr>
              {peajes.map(p => (
                <td key={p.nombre}>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    /* 1) mostramos porcentaje */
                    value={toPct(p.peaje)}
                    /* 2) guardamos fracción */
                    onChange={e =>
                      handlePeajeValueChange(p.nombre, toFrac(parseFloat(e.target.value)))
                    }
                    className="tc-peaje-input"
                  />
                  <span style={{ marginLeft: 4 }}>%</span>
                </td>
              ))}
            </tr>
          </tbody>
          </table>

          <div className="tc-peajes-guardar">
            <button className="tc-btn-save" onClick={saveAll} disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      </div>


    </div>
  );
  
  
}
