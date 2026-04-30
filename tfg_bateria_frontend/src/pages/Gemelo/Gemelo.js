/* Gemelo.jsx
 * Gemelo digital de consumo y predicción energética
 *
 *  1. Imports
 *  2. Utilidades puras
 *  3. Constantes
 *  4. Hooks personalizados
 *  5. Componente Gemelo
 */

import React, {
  useState,
  useEffect,
  useMemo,
  useCallback,
} from 'react';
import Plot from 'react-plotly.js';
import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  ResponsiveContainer,
} from 'recharts';

import MultiIntervalSlider from '../../components/MultiIntervalSlider';
import ChartsEnergia from './ChartsEnergia';
import TarifaIndicator from './TarifaIndicador';
import ChartsConsumo from './ConsumoManualChart';
import HumedadManualChart from './HumedadManualChart';
import ModoAhorroHeatmap from './ModoAhorroHeatmap';
import EventosCriticos from './EventosCriticos';

import { useAuth } from '../../context/AuthContext';
import { useManualPrediction } from '../../hooks/useManualPrediction';
import { useApi } from '../../hooks/useApi';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import '../../assets/styles/Gemelo.css';


/* ========== 1. Utilidades puras ========== */

const parseTimeToMinutes = (time) => {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
};

const minutesToTime = (mins) => {
  const h = String(Math.floor(mins / 60)).padStart(2, '0');
  const m = String(mins % 60).padStart(2, '0');
  return `${h}:${m}`;
};

export const getMonday = (d = new Date()) => {
  const day = d.getDay(); // 0-6 (0 dom)
  const diff = (day === 0 ? -6 : 1) - day;
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + diff, 0, 0, 0);
};

/* ========== 2. Constantes ========== */

export const DAYS = [
  'LUNES',
  'MARTES',
  'MIERCOLES',
  'JUEVES',
  'VIERNES',
  'SABADO',
  'DOMINGO',
];

const DIAS_VACIO = Object.fromEntries(DAYS.map(d => [d, []]));
const RADIAL_COLORS = {
  Actual: "#276EF1",
  Optimizado: "#21BF73",
  Usuario: "#FF8300"
};

/* ========== 3. Hooks personalizados ========== */

const ymdLocal = d =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()
  ).padStart(2, '0')}`;

function useAvailableDates(disableFetch) {
  const api = useApi();
  const [dates, setDates] = useState([]);

  useEffect(() => {
    if (disableFetch) return;

    (async () => {
      try {
        const [{ start, end }] = await api.get('/fechas/disponibles');

        const tmp = [];
        // creamos las fechas al “mediodía” para evitar saltos de huso
        const startDate = new Date(`${start}T12:00`);
        const endDate   = new Date(`${end}T12:00`);

        for (
          let cursor = new Date(startDate);
          cursor <= endDate;
          cursor.setDate(cursor.getDate() + 1)
        ) {
          tmp.push(ymdLocal(cursor));      // ← sin UTC
        }

        setDates(tmp);
      } catch (err) {
        console.error('Error al cargar fechas disponibles:', err);
      }
    })();
  }, [disableFetch]);

  return dates;
}

function useSchedules(date, disableFetch) {
  const api = useApi();
  const [real, setReal] = useState([]);
  const [opt, setOpt] = useState([]);

  useEffect(() => {
    if (disableFetch || !date) return;

    const toIntervals = (arr = []) =>
      arr.map(({ inicio_ahorro, final_ahorro }) => ({
        start: parseTimeToMinutes(inicio_ahorro.slice(11, 16)),
        end: parseTimeToMinutes(final_ahorro.slice(11, 16)),
      }));

    (async () => {
      try {
        const [{ schedule: realSch }, { schedule: optSch }] = await Promise.all([
          api.get(`/planificacion/dia?start_date=${date}`),
          api.get(`/planificacion/optimizada?start_date=${date}`),
        ]);

        setReal(toIntervals(realSch));
        setOpt(toIntervals(optSch));
      } catch (err) {
        console.error('Error al cargar schedules:', err);
      }
    })();
  }, [date, disableFetch]);

  return { real, opt };
}

/* ========== 4. Componente principal ========== */

function Gemelo({ disableFetch = false }) {
  // Contexto & navegación
  const navigate = useNavigate();
  const { user } = useAuth();
  const api = useApi();
  const queryClient = useQueryClient();
  const isEditor = user?.is_editor;

  // Fechas
  const availableDates = useAvailableDates(disableFetch);
  const todayStr = new Date().toISOString().slice(0, 10);
  const [selectedDate, setSelectedDate] = useState(todayStr);
  const isToday = selectedDate === todayStr;
  const isTodayOrFuture = selectedDate >= todayStr;

  // Schedules
  const { real: sliderReal, opt: sliderOpt } = useSchedules(
    selectedDate,
    disableFetch,
  );
  const [sliderManual, setSliderManual] = useState([]);

  // Plan seleccionado
  const [selectedPlan, setSelectedPlan] = useState('Manual');

  // Consumos y totales
  const [consReal, setConsReal] = useState([]);
  const [totalReal, setTotalReal] = useState(0);

  const [consOpt, setConsOpt] = useState([]);        // Optimizado
  const [totalOpt, setTotalOpt] = useState(0);

  const [consPredManual, setConsPredManual] = useState([]);
  const [totalManual, setTotalManual] = useState(0);

  const [consumoManual, setConsumoManual] = useState([]);
  const [humedadManual, setHumedadManual] = useState([]);

  // Otros estados
  const [isSending, setIsSending] = useState(false);

  // Mutaciones
  const manualPrediction = useManualPrediction(disableFetch);

  // Helpers para schedules
  const toSchedule = useCallback(
    (arr) =>
      arr.map(({ start, end }) => ({
        inicio_ahorro: minutesToTime(start),
        final_ahorro: minutesToTime(end),
      })),
    [],
  );

  /* ==================== Effects ==================== */

  // Reset estado manual cuando cambia la fecha
  useEffect(() => {
    setConsPredManual([]);
    setConsumoManual([]);
    setHumedadManual([]);
    setTotalManual(0);
    setSliderManual([]);

    const cached = queryClient.getQueryData(['manualPrediction', selectedDate]);
    const cachedIntervals = queryClient.getQueryData(['manualIntervals', selectedDate]);
    if (cached) {
      setConsPredManual(cached.data);
      setTotalManual(cached.total_cost_eur);
      setConsumoManual(cached.datasets ?? []);
      setHumedadManual(cached.humedad ?? []);
      if (cachedIntervals) setSliderManual(cachedIntervals);
    }
  }, [selectedDate, queryClient]);

  // Carga consumo real
  useEffect(() => {
    if (disableFetch || !selectedDate) return;

    (async () => {
      try {
        const { data, total_cost_eur } = await api.get(
          `/consumo/real?fecha=${selectedDate}`,
        );
        setConsReal(data);
        setTotalReal(total_cost_eur);
      } catch (err) {
        console.error('Error consumo_real:', err);
      }
    })();
  }, [selectedDate, disableFetch]);

  // Carga consumo optimizado
  useEffect(() => {
    if (disableFetch || !selectedDate) return;
    (async () => {
      try {
        const { data, total_cost_eur } = await api.get(
          `/consumo/optimizado?fecha=${selectedDate}`,
        );
        setConsOpt(data);
        setTotalOpt(total_cost_eur);
      } catch (err) {
        console.error('Error consumo_opt:', err);
      }
    })();
  }, [selectedDate, disableFetch]);

  /* ==================== Callbacks ==================== */

  // Predicción manual
  const handleSendManualPrediction = async () => {
    if (!selectedDate) return;
    setIsSending(true);

    manualPrediction.mutate(
      {
        schedule: toSchedule(sliderManual),
        intervals: sliderManual,
        selectedDate,
      },
      {
        onSuccess: (json) => {
          if (!json) return;
          setConsPredManual(json.data);
          setTotalManual(json.total_cost_eur);
          setConsumoManual(json.datasets ?? []);
          setHumedadManual(json.humedad  ?? []);
        },
        onError: (err) => console.error('Predicción manual:', err),
        onSettled: () => setIsSending(false),
      },
    );
  };

  // Abrir planificador
  const handleOpenPlanificador = () => {
    if (!isEditor) return;
    const monday     = getMonday(new Date(selectedDate));
    const weekStart  = ymdLocal(monday);
    const editingDay = DAYS[(new Date(selectedDate).getDay() + 6) % 7];

    const intervals =
      selectedPlan.toLowerCase() === 'optimizado'
        ? sliderOpt
        : sliderManual;

    const proposedWeek = { ...DIAS_VACIO };
    proposedWeek[editingDay] = intervals.map(({ start, end }) => ({ start, end }));

    navigate('/planificador', {
      state: {
        weekStart,
        editingDay,
        selectedPlan: selectedPlan.toLowerCase(),
        proposedSchedulerData: {
          [weekStart]: proposedWeek,
        },
      },
    });
  };

  /* ==================== Data derivada ==================== */

  const plotData = useMemo(
    () => [
      {
        x: consReal.map((i) => i.hora),
        y: consReal.map((i) => i.coste_kwh),
        name: 'Consumo Real',
        type: 'bar',
        marker: { color: RADIAL_COLORS.Actual },
      },
      {
        x: consOpt.map((i) => i.hora),
        y: consOpt.map((i) => i.coste_kwh),
        name: 'Consumo Optimizado',
        type: 'bar',
        marker: { color: RADIAL_COLORS.Optimizado },
      },
      {
        x: consPredManual.map((i) => i.hora),
        y: consPredManual.map((i) => i.coste_kwh),
        name: 'Consumo Personalizado',
        type: 'bar',
        marker: { color: RADIAL_COLORS.Usuario },
      },
    ],
    [consReal, consOpt, consPredManual],
  );

  const radialData = useMemo(
    () => [
      { name: 'Actual', value: totalReal },
      { name: 'Optimizado', value: totalOpt },
      { name: 'Usuario', value: totalManual },
    ],
    [totalReal, totalOpt, totalManual],
  );

  /* ==================== Render ==================== */

  return (
    <>
      <div className="gemelo-container">
        {/* ---------------- Left ---------------- */}
        <div className="left-section">
          {/* Fecha */}
          <div className="date-picker-group">
            <label htmlFor="fecha_grafica">Fecha:</label>
            <input
              type="date"
              id="fecha_grafica"
              value={selectedDate}
              min={availableDates[0]}
              max={availableDates.at(-1)}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
          </div>

          {/* Sliders */}
          {[
            {
              key: 'Actual',
              data: sliderReal,
              setData: () => {},
              disabled: true,
              radio: false,
            },
            {
              key: 'Optimizado',
              data: sliderOpt,
              setData: () => {},
              disabled: true,
              radio: true,
            },
            {
              key: 'Personalizado',
              data: sliderManual,
              setData: setSliderManual,
              disabled: false,
              radio: true,
            },
          ].map(({ key, data, setData, disabled, radio }) => (
            <div
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                margin: '1rem 0',
              }}
            >
              <div
                style={{
                  width: '120px',
                  marginRight: '1rem',
                  fontWeight: 600,
                  textAlign: 'right',
                }}
              >
                {key}
              </div>

              {radio ? (
                <input
                  type="radio"
                  name="plan-selector"
                  checked={selectedPlan === key}
                  onChange={() => setSelectedPlan(key)}
                  disabled={!isEditor}
                  style={{ marginRight: '1rem' }}
                />
              ) : (
                <div style={{ width: 20, marginRight: '1rem' }} />
              )}

              <MultiIntervalSlider
                intervals={data}
                onChange={setData}
                disabled={disabled}
              />
            </div>
          ))}

          {/* Acciones */}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
            <button
              className="btn-send-scheduler"
              onClick={handleSendManualPrediction}
              disabled={isSending}
            >
              {isSending ? 'Enviando...' : 'Planificar'}
            </button>

            <button
              className={`btn-send-scheduler ${
                !isEditor || !(isTodayOrFuture) ? 'disabled-visual' : ''
              }`}
              onClick={handleOpenPlanificador}
              disabled={!isEditor}
            >
              Establecer Plan de Consumo
            </button>
          </div>

          {/* Gráfica consumo */}
          <div className="plot-section" style={{ flex: 1, minHeight: 0, height: '100%' }}>
            <Plot
              data={plotData}
              layout={{
                title: { text: 'Consumo por hora', font: { size: 18 } },
                xaxis: { title: { text: 'Hora', standoff: 10 }, automargin: true },
                yaxis: { title: { text: 'Consumo (€)', standoff: 10 }, automargin: true },
                margin: { t: 70, r: 10, b: 70, l: 10 }
              }}
              useResizeHandler
              style={{ width: '100%', height: '100%' }}
            />
          </div>
        </div>

        {/* ---------------- Right ---------------- */}
        <div className="right-section">
          {/* Totales radiales */}
          <div className="radial-grid">
            {radialData.map((item) => (
              <div key={item.name} className="radial-item">
                <ResponsiveContainer width="100%" aspect={1}>
                  <RadialBarChart
                    data={[item]}
                    cx="50%"
                    cy="50%"
                    innerRadius="70%"
                    outerRadius="100%"
                    startAngle={90}
                    endAngle={-270}
                  >
                    <PolarAngleAxis
                      type="number"
                      domain={[0, Math.max(item.value, 20)]}
                      tick={false}
                    />
                    <RadialBar
                      dataKey="value"
                      clockWise
                      cornerRadius={10}
                      background={{ fill: '#eee' }}
                      fill={RADIAL_COLORS[item.name] || "#888"} 
                    />
                    <text
                      x="50%"
                      y="50%"
                      textAnchor="middle"
                      dominantBaseline="middle"
                      style={{ fontSize: '10px' }}
                    >
                      {item.name}: {item.value.toFixed(2)} €
                    </text>
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>

          {/* Heatmap + eventos críticos */}
          <ModoAhorroHeatmap selectedDate={selectedDate} />
          <EventosCriticos focusDate={selectedDate} />
        </div>
      </div>

      {/* Indicadores y gráficas adicionales */}
      <TarifaIndicator date={selectedDate} />
      <ChartsEnergia
        focusDate={selectedDate}
        ahorroActivo={sliderReal}
        ahorroOpt={sliderOpt}
      />

      {consumoManual.length > 0 && (
        <ChartsConsumo consumoManual={consumoManual} />
      )}
      {humedadManual.length > 0 && (
        <HumedadManualChart humedadManual={humedadManual} />
      )}
    </>
  );
}

export default Gemelo;
