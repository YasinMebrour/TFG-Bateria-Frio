// File: UsuariosConfigPage.jsx – versión simplificada con 3 sliders únicos

import React, { useState, useEffect } from "react";
import Plot from "react-plotly.js";
import '../../assets/styles/ConfigPredi.css';
import { useAuth } from '../../context/AuthContext';


export default function UsuariosConfigPage() {
    const { authFetch } = useAuth();

  /* ---------- configuración backend existente ---------- */
  const [bandaTemp,       setBandaTemp]   = useState("");
  const [bandaHumedad,    setBandaHumedad]= useState("");
  const [bandaPreState,   setBandaPreState]=useState("");
  const [numRangos,       setNumRangos]   = useState("");
  const [horasTotales,    setHorasTotales]= useState("");
  const [horasMaxAhorro,    setHorasMaxAhorro]= useState("");
  const [horasMaxEntreAhorro,    setHorasMaxEntreAhorro]= useState("");
  const [modoAhorroActivo,setModoAhorroActivo]=useState(false);
  const [horaEnvio, setHoraEnvio] = useState("");
  const [diasAhorro, setDiasAhorro] = useState(
        () => ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    );

  const days =[
      "LUNES", "MARTES", "MIERCOLES",
    "JUEVES", "VIERNES", "SABADO", "DOMINGO",
  ]

  const diasSemanaPorDefecto = [
      "LUNES", "MARTES", "MIERCOLES",
    "JUEVES", "VIERNES",
  ]


  const toggleDiaAhorro = d =>
        setDiasAhorro(prev =>
            prev.includes(d)
                ? prev.filter(x => x !== d)
                : [...prev, d]
        );

  

  /* ---------- nuevo: 3 sliders únicos (1‒5) ---------- */
  const [pesos, setPesos] = useState({ manual: 1, optimizado: 2, semanal: 3 });

  const setPeso = (key, val) => {
    val = Number(val);
    // si ya está usado por otro slider, intercambiamos valores
    const conflictKey = Object.keys(pesos).find(k => k !== key && pesos[k] === val);
    setPesos(prev => {
      const next = { ...prev, [key]: val };
      if (conflictKey) {
        next[conflictKey] = prev[key]; // simple swap
      }
      return next;
    });
  };

  /* ----------  fetch fechas disponibles --------------------------- */
  const [minDate, setMinDate] = useState("");   
  const [maxDate, setMaxDate] = useState("");
  const ymdLocal = d =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()
  ).padStart(2, '0')}`;

  useEffect(() => {

    (async () => {
      try {
        const res = await authFetch('http://localhost:8000/fechas/disponibles');
        const [{ start, end }] = await res.json();

        const tmp = [];
        // creamos las fechas al “mediodía” para evitar saltos de huso
        const startDate = new Date(`${start}T12:00`);
        const endDate   = new Date(`${end}T12:00`);

        for (
          let cursor = new Date(startDate);
          cursor <= endDate;
          cursor.setDate(cursor.getDate() + 1)
        ) {
          tmp.push(ymdLocal(cursor));     
        }

        setMinDate(tmp[0]);             
        setMaxDate(tmp[tmp.length - 1]);
      } catch (err) {
        console.error('Error al cargar fechas disponibles:', err);
      }
    })();
  }, []);

  /* ---------- banda pre dinámica y gráfico (sin cambios) ---------- */
  const [bandaPre, setBandaPre] = useState(null);
  const [start, setStart]       = useState("");
  const [end, setEnd]           = useState("");
  const [datos, setDatos]       = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await authFetch("http://localhost:8000/config/");
        if (!res.ok) throw new Error("No se pudo cargar config");
        const cfg = await res.json();
        setBandaTemp(cfg.banda_seguridad_temperatura ?? "");
        setBandaHumedad(cfg.banda_seguridad_humedad ?? "");
        setBandaPreState(cfg.banda_condiciones_optimas ?? "");
        setNumRangos(cfg.rangos_ahorro ?? "");
        setHorasTotales(cfg.horas_modo_ahorro ?? "");
        setHorasMaxAhorro(cfg.horas_max_ahorro ?? "");
        setHorasMaxEntreAhorro(cfg.horas_max_entre_ahorro ?? "");
        setModoAhorroActivo(cfg.ahorro_energia_habilitado);
        setHoraEnvio(cfg.hora_envio_planificacion ?? "");
        if (cfg.pesos_unicos) setPesos(cfg.pesos_unicos);

        // --- NUEVO: cargar días activos desde cfg.dias_ahorro (si existe)
        if (cfg.dias_ahorro) {
          // Pasa el dict { lunes: true, ... } a array ["LUNES", ...]
          const activos = Object.entries(cfg.dias_ahorro)
            .filter(([k, v]) => v)
            .map(([k]) => k.toUpperCase());
          setDiasAhorro(activos);
        } else {
          setDiasAhorro(diasSemanaPorDefecto); // fallback por si no está en backend
        }
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);


  /* ---------- guardar ---------- */
  const handleGuardar = async () => {
    const payload = {
      banda_seguridad_temperatura: parseFloat(bandaTemp)||null,
      banda_seguridad_humedad:     parseFloat(bandaHumedad)||null,
      banda_condiciones_optimas:   parseFloat(bandaPreState)||null,
      ahorro_energia_habilitado:   modoAhorroActivo,
      rangos_ahorro:               parseInt(numRangos)||null,
      horas_modo_ahorro:           parseFloat(horasTotales)||null,
      horas_max_ahorro:            parseFloat(horasMaxAhorro)||null,
      horas_max_entre_ahorro:      parseFloat(horasMaxEntreAhorro)||null,
      pesos_unicos:                pesos,
      hora_envio_planificacion: horaEnvio || null,
      dias_ahorro: diasAhorroToDict(diasAhorro),    // <--- aquí
    };
    try {
      const r = await authFetch("http://localhost:8000/config/",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(payload)
      });
      if(!r.ok) throw new Error("Error guardando");
    } catch(e){console.error(e);}
  };


  /* ---------- fetch banda_pre_ahorro ---------- */
  useEffect(()=>{
    if(!start||!end) return;
    (async()=>{
      try{
        const res = await authFetch(`http://localhost:8000/banda_pre_ahorro?start=${start}&end=${end}`);
        if(!res.ok) throw new Error(res.statusText);
        const j = await res.json();
        setBandaPre(j.banda); setDatos(j.datos);
      }catch(e){console.error(e);} })();
  },[start,end]);

  const bajada = datos.filter(d=>d.estado===0);
  const subida = datos.filter(d=>d.estado===1);

  const handleToggleModoAhorro = () => {
      setModoAhorroActivo(prev => {
          const next = !prev;
          if (next) setDiasAhorro(diasSemanaPorDefecto); // al activar, pones días por defecto
          return next;
      });
  };

  const daysKeys = [
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"
  ];
  const daysLabelMap = {
    "LUNES": "lunes",
    "MARTES": "martes",
    "MIERCOLES": "miercoles",
    "JUEVES": "jueves",
    "VIERNES": "viernes",
    "SABADO": "sabado",
    "DOMINGO": "domingo"
  };

  function diasAhorroToDict(diasAhorro) {
    // Convierte el array en un objeto { lunes: true/false, ... }
    const selected = diasAhorro.map(d => daysLabelMap[d]);
    const dict = {};
    for (const k of daysKeys) {
      dict[k] = selected.includes(k);
    }
    return dict;
  }

  const [errores, setErrores] = useState({});

  // Validación de restricciones lógicas
  useEffect(() => {
    const errs = {};

    // Horas totales >= rangos * horas máximas en intervalo
    if (
      Number(numRangos) > 0 &&
      Number(horasMaxAhorro) > 0 &&
      Number(horasTotales) > 0 &&
      Number(horasTotales) > Number(numRangos) * Number(horasMaxAhorro)
    ) {
      errs.horasTotales = 'Las horas totales deben ser al menos igual al número de rangos por las horas máximas en intervalo.';
    }

    // Horas mínimas entre ahorros >= 0
    if (Number(horasMaxEntreAhorro) < 0) {
      errs.horasMaxEntreAhorro = 'Las horas mínimas entre ahorros no pueden ser negativas.';
    }

    // Horas máximas en intervalo <= horas totales
    if (
      Number(horasMaxAhorro) > 0 &&
      Number(horasTotales) > 0 &&
      Number(horasMaxAhorro) > Number(horasTotales)
    ) {
      errs.horasMaxAhorro = 'Las horas máximas en intervalo no pueden ser mayores que las horas totales.';
    }

    setErrores(errs);
  }, [numRangos, horasMaxAhorro, horasTotales, horasMaxEntreAhorro]);



  /* ---------- UI ---------- */
  return (
  <div className="config-container">
    {/* ▸ panel izquierdo */}
    <div className="config-left">

      {/* parámetros de bandas (fuera del grupo) */}
      {[
        {id:'input-banda-temp', label:'Banda Seguridad Temp (ºC)', value:bandaTemp, onChange:setBandaTemp, step:'0.1'},
        {id:'input-banda-hum',  label:'Banda Seguridad Hum (%)',  value:bandaHumedad, onChange:setBandaHumedad, step:'0.1'},
        {id:'input-banda-pre',  label:'Banda Pre Ahorro (min)',   value:bandaPreState, onChange:setBandaPreState, step:'0.1'},
      ].map(({id,label,value,onChange,step,type='number'})=> (
        <div key={id} className="config-row">
          <label className="config-label" htmlFor={id}>{label}</label>
          <input id={id} type={type} step={step} className="config-input" value={value} onChange={e=>onChange(e.target.value)} />
        </div>
      ))}

      {/* GRUPO HORAS Y RANGOS */}
      <div className="config-group grupo-horas">
        <h5 className="grupo-title">Horas y Rangos</h5>

        <div className="config-row">
          <label className="config-label" htmlFor="input-rangos">N.º rangos ahorro</label>
          <input id="input-rangos" type="number" className="config-input"
                 value={numRangos} onChange={e=>setNumRangos(e.target.value)} />
        </div>

        <div className="config-row">
          <label className="config-label" htmlFor="input-horas-totales">Horas totales ahorro</label>
          <input id="input-horas-totales" type="number" className="config-input"
                 value={horasTotales} onChange={e=>setHorasTotales(e.target.value)} />
          {errores.horasTotales && (
            <div className="input-error">{errores.horasTotales}</div>
          )}
        </div>

        <div className="config-row">
          <label className="config-label" htmlFor="input-horas-max-intervalo">Horas máximas en intervalo de ahorro</label>
          <input id="input-horas-max-intervalo" type="number" className="config-input"
                 value={horasMaxAhorro} onChange={e=>setHorasMaxAhorro(e.target.value)} />
          {errores.horasMaxAhorro && (
            <div className="input-error">{errores.horasMaxAhorro}</div>
          )}
        </div>

        <div className="config-row">
          <label className="config-label" htmlFor="input-horas-min-entrelos">Horas mínimas entre ahorros</label>
          <input id="input-horas-min-entrelos" type="number" className="config-input"
                 value={horasMaxEntreAhorro} onChange={e=>setHorasMaxEntreAhorro(e.target.value)} />
          {errores.horasMaxEntreAhorro && (
            <div className="input-error">{errores.horasMaxEntreAhorro}</div>
          )}
        </div>
      </div>
      {/* FIN GRUPO */}

      {/* Hora envío (fuera del grupo) */}
      <div className="config-row">
        <label className="config-label" htmlFor="input-envio">Hora envío planificación</label>
        <input id="input-envio" type="time" className="config-input" value={horaEnvio} onChange={e=>setHoraEnvio(e.target.value)} />
      </div>

      <div className="config-ahorro-row">
        <button
          type="button"
          className={`btn-toggle ${modoAhorroActivo ? 'active' : 'inactive'}`}
          onClick={handleToggleModoAhorro}
        >
          Modo Ahorro: {modoAhorroActivo ? 'Sí' : 'No'}
        </button>

        {modoAhorroActivo && (
          <div className="dias-ahorro-panel">
            {days.map(d => (
              <label key={d} className="dias-ahorro-label">
                <input
                  type="checkbox"
                  checked={diasAhorro.includes(d)}
                  onChange={() => toggleDiaAhorro(d)}
                />
                {d.toUpperCase()}
              </label>
            ))}
          </div>
        )}
      </div>
     
      <button
        className="btn-submit"
        onClick={handleGuardar}
        disabled={Object.keys(errores).length > 0}
      >
        Guardar
      </button>
    </div>

    {/* ▸ panel derecho */}
    <div className="config-right">
      <div className="config-row center-row"><h4>Banda Pre Ahorro Informativo</h4></div>
      <div className="config-row date-pair">
        <div className="date-group">
          <label className="config-label label-inline" htmlFor="input-start">Inicio</label>
          <input id="input-start" type="datetime-local" className="config-input datetime" value={start} min={`${minDate}T00:00`} max={`${maxDate}T23:59`} onChange={e=>setStart(e.target.value)} />
        </div>
        <div className="date-group">
          <label className="config-label label-inline" htmlFor="input-end">Fin</label>
          <input id="input-end" type="datetime-local" className="config-input datetime" value={end} min={`${minDate}T00:00`} max={`${maxDate}T23:59`} onChange={e=>setEnd(e.target.value)} />
        </div>
      </div>
      <div className="plot-section">
        <Plot
          data={[
            {x:bajada.map(d=>d.hora),y:bajada.map(d=>d.humedad),mode:'markers',type:'scatter',name:'Bajada',marker:{color:'#ff4c4c',size:6}},
            {x:subida.map(d=>d.hora),y:subida.map(d=>d.humedad),mode:'markers',type:'scatter',name:'Subida',marker:{color:'#0070bf',size:6}}
          ]}
          layout={{xaxis:{title:'Hora',type:'date'},yaxis:{title:'Humedad'},margin:{t:20,b:50,l:60,r:30},height:350,hovermode:'closest'}}
          config={{responsive:true,displayModeBar:true}} style={{width:'100%'}} />
      </div>
      <div className="bottom-text"><strong>Banda:</strong> {bandaPre?.toFixed(1)??'—'} minutos</div>
    </div>
  </div>
);


}
