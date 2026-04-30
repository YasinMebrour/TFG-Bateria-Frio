// src/hooks/useBuckets.js
import { useQuery } from '@tanstack/react-query';
import { getBuckets } from '../services/api';
import { QUERY_KEYS } from '../constants/queryKeys';

export function useBuckets(authFetch) {
  return useQuery({
    queryKey: QUERY_KEYS.buckets,
    queryFn: () => getBuckets(authFetch),
    staleTime: 5 * 60_000,
  });
}
