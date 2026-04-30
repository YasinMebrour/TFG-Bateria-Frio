export function formatDuration(seconds) {
  const sec = Number(seconds) || 0;
  if (sec % 86400 === 0 && sec >= 86400) {
    const days = sec / 86400;
    return days === 1 ? '1 día' : `${days} días`;
  }
  if (sec % 3600 === 0 && sec >= 3600) {
    const hours = sec / 3600;
    return hours === 1 ? '1 h' : `${hours} h`;
  }
  if (sec % 60 === 0 && sec >= 60) {
    const mins = sec / 60;
    return mins === 1 ? '1 min' : `${mins} min`;
  }
  return `${sec}s`;
}
