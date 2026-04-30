import React, { useMemo } from 'react';
import { Range } from 'react-range';

const STEP = 60; // 1 hora
const MIN = 0; // 00:00
const MAX = 1440; // 24:00

const minutesToTime = (m) => {
  const h = Math.floor(m / 60);
  const s = m % 60;
  return `${String(h).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

export default function SingleDaySlider({ intervals, onChange, maxIntervals = 3, disabled = false }) {
  const values = useMemo(
    () =>
      intervals
        .slice()
        .sort((a, b) => a.start - b.start)
        .flatMap((i) => [i.start, i.end]),
    [intervals]
  );

  const handleSliderChange = (newVals) => {
    if (disabled) return;
    const sorted = newVals.slice().sort((a, b) => a - b);
    const next = [];
    for (let i = 0; i < sorted.length; i += 2) {
      next.push({ start: sorted[i], end: sorted[i + 1] ?? sorted[i] + STEP });
    }
    onChange(next);
  };

  const handleTrackDoubleClick = (e) => {
    if (disabled || (maxIntervals && intervals.length >= maxIntervals)) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const xPerc = (e.clientX - rect.left) / rect.width;
    const minute = Math.round((MIN + xPerc * (MAX - MIN)) / STEP) * STEP;
    const start = Math.max(MIN, Math.min(MAX - STEP, minute));
    const end = start + STEP;
    onChange([...intervals, { start, end }]);
  };

  const removeInterval = (idx) => {
    if (disabled) return;
    onChange(intervals.filter((_, i) => i !== idx));
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
                        ? 'rgba(0,0,0,0.5)'
                        : 'rgba(33,150,243,0.5)',
                      userSelect: 'none',
                      zIndex: 1,
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
              height: 20,
              width: 20,
              borderRadius: '50%',
              background: disabled ? '#999' : '#2196f3',
              cursor: disabled ? 'not-allowed' : 'grab',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              userSelect: 'none',
              zIndex: 2,
            }}
          >
            <span style={{ position: 'absolute', top: -28, fontSize: 12 }}>
              {minutesToTime(values[index])}
            </span>
          </div>
        )}
      />
    </div>
  );
}
