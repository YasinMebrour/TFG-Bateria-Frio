// src/hooks/useSliderManual.js
import { useState, useEffect } from 'react';

export function useSliderManual(selectedDate, defaultIntervals) {
  const STORAGE_KEY = `sliderManual_${selectedDate}`;

  const [sliderManual, setSliderManual] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : defaultIntervals;
    } catch {
      return defaultIntervals;
    }
  });

  // Al cambiar selectedDate o sliderManual, persistimos
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sliderManual));
    } catch {}
  }, [STORAGE_KEY, sliderManual]);

    // Al cambiar la fecha, recargamos del storage lo que hubiera
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        setSliderManual(JSON.parse(saved));
      } else {
        // si no hay nada guardado, dejamos el slider vacío
        setSliderManual(defaultIntervals);
      }
    } catch {
      setSliderManual(defaultIntervals);
    }
  }, [STORAGE_KEY/* sólo depende de la fecha */]);


  return [sliderManual, setSliderManual];
}
