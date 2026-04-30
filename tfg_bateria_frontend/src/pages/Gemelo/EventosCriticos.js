import React, { useEffect, useState, useRef } from 'react';
import '../../assets/styles/EventosCriticos.css';
import { useAuth } from '../../context/AuthContext';
import { API_URL } from '../../config/apiConfig';
const WS_URL = API_URL.replace(/^http/, 'ws') + '/eventos/ws';

export default function EventosCriticos({ focusDate }) {
  const { token, authFetch } = useAuth();
  const [eventos, setEventos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nuevosEventos, setNuevosEventos] = useState([]);
  const [inicio, setInicio] = useState('');
  const [fin, setFin] = useState('');
  const listRef = useRef(null);

  // Obtener rango por defecto basándonos en los eventos guardados
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const res = await authFetch(`${API_URL}/eventos/rango`);
        if (res.ok) {
          const data = await res.json();
          setInicio(data.inicio.slice(0, 10));
          setFin(data.fin.slice(0, 10));
        }
      } catch (err) {
        console.error('Error obteniendo rango de eventos:', err);
      }
    })();
  }, [token, authFetch]);

  useEffect(() => {
    if (!token) return;
    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);

    ws.onopen = () => {
      ws.send(JSON.stringify({ accion: "historial", fecha: focusDate }));
    };

    ws.onmessage = e => {
      try {
        const nuevos = JSON.parse(e.data);
        const esArray = Array.isArray(nuevos) ? nuevos : [nuevos];

        setEventos(prev => {
          // Para evitar duplicados
          const idsPrevios = new Set(prev.map(ev => ev.id));
          return [...prev, ...esArray.filter(ev => !idsPrevios.has(ev.id))];
        });

        // Si el evento es en tiempo real (no es el historial)
        if (esArray.length && esArray[0].id) {
          const nuevosParaBadge = esArray.filter(ev => ev.fecha && ev.fecha.slice(0, 10) !== focusDate);
          if (nuevosParaBadge.length > 0) {
            setNuevosEventos(prev => [...prev, ...nuevosParaBadge]);
          }
        }

        if (loading) setLoading(false);
      } catch (err) {
        console.error('Error parseando WS:', err);
      }
    };
    ws.onclose = () => console.log('WebSocket desconectado');
    return () => { ws.close(); };
  }, [token, focusDate]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  });

  const descargarInforme = async () => {
    try {
      const inicioParam = `${inicio}T00:00:00`;
      const finParam = `${fin}T23:59:59`;
      const res = await authFetch(
        `${API_URL}/eventos/reporte?inicio=${encodeURIComponent(
          inicioParam
        )}&fin=${encodeURIComponent(finParam)}`
      );
      if (!res.ok) throw new Error('Error generando informe');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'informe_eventos.pdf';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error descargando informe:', err);
    }
  };

  // Si el usuario vuelve al día actual, limpiamos los nuevos eventos
  useEffect(() => {
    if (focusDate === (new Date()).toISOString().slice(0, 10)) {
      setNuevosEventos([]);
    }
  }, [focusDate]);

  const eventosFiltrados = eventos.filter(
    ev => ev.fecha && ev.fecha.slice(0, 10) === focusDate
  );

  return (
    <div className="eventos-criticos-wrapper">
      <div style={{ display: "flex", alignItems: "center" }}>
        {nuevosEventos.length > 0 &&
          <span style={{
            marginLeft: 8,
            background: "red",
            color: "white",
            borderRadius: "50%",
            width: 22,
            height: 22,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 14
          }}>
            {nuevosEventos.length}
          </span>
        }
      </div>
      <div style={{ display: "flex", gap: "0.5rem", margin: "8px 0" }}>
        <input type="date" value={inicio} onChange={e => setInicio(e.target.value)} />
        <input type="date" value={fin} onChange={e => setFin(e.target.value)} />
        <button onClick={descargarInforme}>Descargar informe</button>
      </div>
      <div className="eventos-scroll" ref={listRef}>
        {loading ? (
          <p className="sin-eventos">Cargando eventos…</p>
        ) : eventosFiltrados.length === 0 ? (
          <p className="sin-eventos">Sin eventos</p>
        ) : (
          [...eventosFiltrados].reverse().map((ev, i) => {
            const fecha = ev.fecha.slice(0, 10);
            const hora = ev.fecha.slice(11, 16);
            return (
              <div key={i} className="evento-box" style={{
                backgroundColor: '#e9ecef',
                color: '#000',
              }}>
                <span className="evento-fecha">{fecha} {hora}</span>
                <span className="evento-nombre">{ev.tipo}</span>
                <span className="evento-descripcion">{ev.descripcion}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
