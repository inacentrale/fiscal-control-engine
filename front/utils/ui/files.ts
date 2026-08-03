export function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} o`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} Ko`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} Mo`;
}
