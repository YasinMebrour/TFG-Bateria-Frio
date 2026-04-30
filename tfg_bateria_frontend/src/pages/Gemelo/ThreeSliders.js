import React, { useState } from 'react';
import { Range } from 'react-range';

// Constantes para los límites y paso del slider
const MIN = 60;
const MAX = 24 * 60;  // minutos en un día
const STEP = 15;      // incrementos de 15 minutos

// Convierte minutos desde medianoche a formato HH:MM
function minutesToTime(minutes) {
  const hrs = String(Math.floor(minutes / 60)).padStart(2, '0');
  const mins = String(minutes % 60).padStart(2, '0');
  return `${hrs}:${mins}`;
}

/**
 * Componente de un solo slider con intervalos
 */
function IntervalsSlider({ values, intervals, onChange, onTrackDoubleClick, onRemoveInterval }) {
  return (
    <div className="intervals-container">
      <fieldset className="schedule-off-mode">
        <div className="flex items-center my-4">
          <legend className="mr-4 m-0">Intervalos para el Día</legend>
          <div className="flex-grow px-4">
            <Range
              values={values}
              step={STEP}
              min={MIN}
              max={MAX}
              onChange={onChange}
              renderTrack={({ props: trackProps, children }) => (
                <div className="relative h-3 w-full">
                  <div
                    ref={trackProps.ref}
                    className="h-full w-full bg-gray-300"
                    onDoubleClick={onTrackDoubleClick}
                    draggable={false}
                    onDragStart={e => e.preventDefault()}
                  >
                    {intervals.map(({ start, end }, i) => {
                      const left = ((start - MIN) / (MAX - MIN)) * 100;
                      const width = ((end - start) / (MAX - MIN)) * 100;
                      return (
                        <div
                          key={i}
                          draggable={false}
                          onDragStart={e => e.preventDefault()}
                          onDoubleClick={e => { e.stopPropagation(); onRemoveInterval(i); }}
                          className="absolute top-0 h-full bg-blue-500 bg-opacity-50 select-none"
                          style={{ left: `${left}%`, width: `${width}%`, WebkitUserDrag: 'none' }}
                        />
                      );
                    })}
                    {children}
                  </div>
                </div>
              )}
              renderThumb={({ props: thumbProps, index }) => (
                <div
                  {...thumbProps}
                  draggable={false}
                  onDragStart={e => e.preventDefault()}
                  className="h-5 w-5 rounded-full bg-blue-500 cursor-grab flex items-center justify-center select-none"
                  style={{ WebkitUserDrag: 'none', ...thumbProps.style }}
                >
                  <span className="absolute -top-7 text-xs select-none">
                    {minutesToTime(values[index])}
                  </span>
                </div>
              )}
            />
          </div>
        </div>
      </fieldset>
    </div>
  );
}

/**
 * Componente que renderiza tres sliders independientes
 */
function ThreeSliders() {
  const initial = { values: [8 * 60, 9 * 60], intervals: [] };
  const [sliders, setSliders] = useState([ { ...initial }, { ...initial }, { ...initial } ]);

  const handleChange = idx => newValues => {
    setSliders(s => s.map((x,i) => i===idx ? { ...x, values: newValues } : x));
  };

  const handleTrackDoubleClick = idx => () => {
    setSliders(s => s.map((x,i) => {
      if (i!==idx) return x;
      const [start,end] = x.values;
      return { ...x, intervals: [ ...x.intervals, { start, end } ] };
    }));
  };

  const handleRemoveInterval = idx => removeIdx => {
    setSliders(s => s.map((x,i) => {
      if (i!==idx) return x;
      return { ...x, intervals: x.intervals.filter((_,j)=>j!==removeIdx) };
    }));
  };

  return (
    <div className="space-y-8">
      {sliders.map((sl, i) => (
        <IntervalsSlider
          key={i}
          values={sl.values}
          intervals={sl.intervals}
          onChange={handleChange(i)}
          onTrackDoubleClick={handleTrackDoubleClick(i)}
          onRemoveInterval={handleRemoveInterval(i)}
        />
      ))}
    </div>
  );
}

/**
 * Componente principal que sustituye tu formulario/lista de intervalos
 */
export default function ScheduleComponent() {
  return (
    <div className="schedule-container">
      <ThreeSliders />
    </div>
  );
}
