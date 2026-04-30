// hooks/useManualPrediction.js
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';


export function useManualPrediction(disableFetch = false) {
  const queryClient = useQueryClient();
    const { authFetch } = useAuth();


  return useMutation({
    mutationFn: async ({ schedule, selectedDate }) => {
      if (disableFetch) {
        console.log('Mock POST /consumo/prediccion/manual', { schedule, selectedDate });
        return null;
      }

      // Enviar la fecha sin zona horaria para que el backend la interprete
      // como Europe/Madrid. Usar timezone UTC provocaba un desplazamiento de
      // dos horas en las predicciones.
      const start_date = selectedDate;

      const res = await authFetch(
        `${process.env.REACT_APP_API_URL}/consumo/prediccion/manual`,
        {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ schedule, start_date }),
        },
      );

      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Error en predicción manual');

      return json;      // ← se propaga a onSuccess
    },

    // --- aquí se actualiza la caché ---
    onSuccess: (json, { selectedDate, intervals }) => {
      if (!json) return;      // modo mock

      // Guarda en caché: key = ['manualPrediction', '2025-05-18']
      queryClient.setQueryData(['manualPrediction', selectedDate], json);
      queryClient.setQueryData(['manualIntervals',  selectedDate], intervals);
    },
  });
}
