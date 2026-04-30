// src/hooks/useMeasurementsByBucket.js
import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { getMeasurements } from '../services/api';

export function useMeasurementsByBucket(buckets = [], openBuckets = new Set(), authFetch) {
  // Disparamos una query por cada bucket, pero sólo cuando está “abierto”
  const results = useQueries({
    queries: buckets.map(bucket => ({
      queryKey: ['measurements', bucket],
      queryFn: () => getMeasurements(bucket, authFetch),
      enabled: openBuckets.has(bucket),
      staleTime: 5 * 60_000,
    }))
  });

  // Construimos el mapa bucket → measurements[]
  return useMemo(() => {
    const map = {};
    buckets.forEach((bucket, i) => {
      map[bucket] = results[i]?.data || [];
    });
    return map;
  }, [buckets, results]);
}
