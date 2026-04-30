// src/hooks/useStoredManualPrediction.js
import { useQueryClient } from '@tanstack/react-query';

export function useStoredManualPrediction(selectedDate) {
  const qc = useQueryClient();
  // recuperamos directamente de la cache de React Query
  const cached = qc.getQueryData(['consumo_manual', selectedDate]);
  return cached || { data: [], total_cost_eur: 0, datasets: [], humedad: [] };
}
