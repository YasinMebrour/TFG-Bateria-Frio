// src/hooks/useFieldsByBucketMeasurement.js
import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { getFieldsByMeasurement } from '../services/api';

export function useFieldsByBucketMeasurement(openMeasurements = new Set(), authFetch) {
  const composites = Array.from(openMeasurements);

  const results = useQueries({
    queries: composites.map(composite => {
      const [bucket, measurement] = composite.split('|');
      return {
        queryKey: ['fields', bucket, measurement],
        queryFn: () => getFieldsByMeasurement(bucket, measurement, authFetch),
        enabled: true,
        staleTime: 5 * 60_000,
      };
    })
  });

  return useMemo(() => {
    const map = {};
    composites.forEach((c, i) => {
      map[c] = results[i]?.data || [];
    });
    return map;
  }, [composites, results]);
}
