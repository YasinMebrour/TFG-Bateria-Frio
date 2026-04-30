import React, { useMemo } from 'react';
import { Range } from 'react-range';

const STEP = 60; // 1 hora en minutos
const MIN = 0; // 00:00
const MAX = 1440; // 24:00

const minutesToTime = (mins) => {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
};

/**
 * Slider para seleccionar multiples intervalos.
 * - intervals: lista de intervalos { start, end }
 * - onChange: callback con los intervalos actualizados
 * - maxIntervals: limite opcional de intervalos (por defecto 3)
 * - disabled: deshabilitar interaccion
 */
export default function MultiIntervalSlider({
  intervals,
  onChange,
  maxIntervals = 3,
  disabled = false,
}) {
  const values = useMemo(
    () =>
      intervals
        .slice()
        .sort((a, b) => a.start - b.start)
        .flatMap((i) => [i.start, i.end]),
    [intervals]
  );

  const handleSliderChange = (newValues) => {
    if (disabled) return;
    const sorted = [...newValues].sort((a, b) => a - b);
    const newIntervals = [];
    for (let i = 0; i < sorted.length; i += 2) {
      newIntervals.push({
        start: sorted[i],
        end: sorted[i + 1] ?? sorted[i] + STEP,
      });
    }
    onChange(newIntervals);
  };

  const handleTrackDoubleClick = (e) => {
    if (disabled || (maxIntervals && intervals.length >= maxIntervals)) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percent = clickX / rect.width;
    const minute = Math.round((MIN + percent * (MAX - MIN)) / STEP) * STEP;
    const start = Math.max(MIN, Math.min(MAX - STEP, minute));
    const end = start + 60;
    onChange((prev) => [...prev, { start, end }]);
  };

  const removeInterval = (idx) => {
    if (disabled) return;
    onChange((prev) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div style={{ flex: 1, padding: '0 1rem' }}>
      <Range
        values={values}
        step={STEP}
        min={MIN}
        max={MAX}
        onChange={handleSliderChange}
        renderTrack={({ props: trackProps, children }) => (
          <div style={{ height: 12, width: '100%', position: 'relative' }}>
            <div
              ref={trackProps.ref}
              style={{ height: '100%', width: '100%', background: '#ddd' }}
              onDoubleClick={handleTrackDoubleClick}
              draggable={false}
              onDragStart={(e) => e.preventDefault()}
            >
              {intervals.map(({ start, end }, i) => {
                const left = ((start - MIN) / (MAX - MIN)) * 100;
                const width = ((end - start) / (MAX - MIN)) * 100;
                return (
                  <div
                    key={i}
                    draggable={false}
                    onDragStart={(e) => e.preventDefault()}
                    onDoubleClick={(e) => {
                      e.stopPropagation();
                      removeInterval(i);
                    }}
                    style={{
                      position: 'absolute',
                      left: `${left}%`,
                      width: `${width}%`,
                      height: '100%',
                      background: disabled
                        ? 'rgba(0, 0, 0, 0.5)'
                        : 'rgba(33,150,243,0.5)',
                      zIndex: 1,
                      userSelect: 'none',
                      WebkitUserDrag: 'none',
                    }}
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
            onDragStart={(e) => e.preventDefault()}
            style={{
              ...thumbProps.style,
              zIndex: 2,
              height: 20,
              width: 20,
              borderRadius: '50%',
              backgroundColor: disabled ? '#999' : '#2196f3',
              cursor: disabled ? 'not-allowed' : 'grab',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              userSelect: 'none',
              WebkitUserDrag: 'none',
            }}
          >
            <span style={{ position: 'absolute', top: -28, fontSize: 12, userSelect: 'none' }}>
              {minutesToTime(values[index])}
            </span>
          </div>
        )}
      />
    </div>
  );
}
