/**
 * Devuelve el payload decodificado o null si el token no es válido.
 */
export function parseJwtPayload(token) {
  if (!token) return null;
  try {
    const [, payload] = token.split(".");
    const padded = payload.padEnd(payload.length + (4 - (payload.length % 4)) % 4, "=");
    const json = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Comprueba que el token existe, tiene `exp` y no ha caducado. */
export function isTokenValid(token) {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return false;
  return payload.exp > Date.now() / 1000;
}

/** Segundos que restan antes de expirar (`0` si ya caducó). */
export function tokenRemainingSeconds(token) {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return 0;
  return Math.max(payload.exp - Date.now() / 1000, 0);
}