const API_URL = "http://127.0.0.1:8000"; // Base URL

/**
 * 1) Obtener la lista de buckets
 */
export async function getBuckets(authFetch) {
  try {
    const res = await authFetch(`${API_URL}/influx/buckets`);
    const data = await res.json();
    // aquí asumo que el endpoint devuelve { buckets: [...] }
    return data.buckets || [];
  } catch (err) {
    console.error("Error fetching buckets:", err);
    return [];
  }
}

/**
 * 2) Obtener los measurements de un bucket concreto
 */
export async function getMeasurements(bucket, authFetch) {
  if (!bucket) {
    console.warn("getMeasurements: falta parámetro bucket");
    return [];
  }
  try {
    const res = await authFetch(`${API_URL}/influx/measurements?bucket=${encodeURIComponent(bucket)}`);
    const data = await res.json();
    return data.measurements || [];
  } catch (err) {
    console.error(`Error fetching measurements for bucket "${bucket}":`, err);
    return [];
  }
}

/**
 * 3) Obtener los fields de un measurement concreto, en un bucket dado
 */
export async function getFieldsByMeasurement(bucket, measurement, authFetch) {
  if (!bucket || !measurement) {
    console.warn("getFieldsByMeasurement: faltan bucket o measurement");
    return [];
  }
  try {
    const res = await authFetch(
      `${API_URL}/influx/fields?bucket=${encodeURIComponent(bucket)}&measurement=${encodeURIComponent(measurement)}`
    );
    const data = await res.json();
    return data.fields || [];
  } catch (err) {
    console.error(`Error fetching fields for "${measurement}" in bucket "${bucket}":`, err);
    return [];
  }
}
