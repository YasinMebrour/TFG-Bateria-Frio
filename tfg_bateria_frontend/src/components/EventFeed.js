import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../hooks/useApi';
import { API_URL } from '../config/apiConfig';
import '../assets/styles/EventFeed.css';

const WS_URL = API_URL.replace(/^http/, 'ws') + '/eventos/ws';

export default function EventFeed() {
  const { token } = useAuth();
  const api = useApi();

  const [events, setEvents] = useState([]);
  const [rules, setRules] = useState([]);
  const [ruleFilter, setRuleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const wsRef = useRef(null);

  // Load available rules once
  useEffect(() => {
    (async () => {
      try {
        const data = await api.get('/reglas');
        setRules(data);
      } catch (err) {
        console.error('Error cargando reglas:', err);
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Connect to WebSocket
  useEffect(() => {
    if (!token) return;

    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;

    ws.onopen = () => {
      const today = new Date().toISOString().slice(0, 10);
      ws.send(JSON.stringify({ accion: 'historial', fecha: today }));
    };

    ws.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        const arr = Array.isArray(payload) ? payload : [payload];
        setEvents((prev) => {
          const ids = new Set(prev.map((ev) => ev.id));
          return [...prev, ...arr.filter((ev) => !ids.has(ev.id))];
        });
      } catch (err) {
        console.error('Error parseando evento WS:', err);
      }
    };

    return () => ws.close();
  }, [token]);

  const uniqueStatus = Array.from(new Set(events.map((ev) => ev.tipo).filter(Boolean)));

  const filtered = events
    .filter((ev) => {
      if (ruleFilter && String(ev.rule_id) !== ruleFilter) return false;
      if (statusFilter && ev.tipo !== statusFilter) return false;
      if (startDate && ev.fecha < `${startDate}T00:00:00`) return false;
      if (endDate && ev.fecha > `${endDate}T23:59:59`) return false;
      return true;
    })
    .sort((a, b) => a.fecha.localeCompare(b.fecha));

  return (
    <div className="event-feed-wrapper">
      <div className="event-feed-filters">
        <select value={ruleFilter} onChange={(e) => setRuleFilter(e.target.value)}>
          <option value="">Todas las reglas</option>
          {rules.map((r) => (
            <option key={r.id} value={r.id}>{r.nombre}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Todos los estados</option>
          {uniqueStatus.map((st) => (
            <option key={st} value={st}>{st}</option>
          ))}
        </select>
        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
      </div>
      <div className="event-feed-list">
        {filtered.length === 0 ? (
          <p className="sin-eventos">Sin eventos</p>
        ) : (
          filtered.map((ev) => (
            <div key={ev.id} className="evento-box">
              <span className="evento-fecha">{ev.fecha.slice(0, 16).replace('T', ' ')}</span>
              <span className="evento-nombre">{ev.tipo}</span>
              <span className="evento-descripcion">{ev.descripcion}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
