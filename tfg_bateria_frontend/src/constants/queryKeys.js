export const QUERY_KEYS = {
  buckets:            ['buckets'],
  measurements:       (bucket) => ['measurements', bucket],
  fields:             (bucket, measurement) => ['fields', bucket, measurement],
  chartData:          (bucket, measurement, field) => ['chartData', bucket, measurement, field],
};
