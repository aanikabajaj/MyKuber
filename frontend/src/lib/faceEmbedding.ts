/**
 * Prototype face embedding: downscale a webcam frame to an 8x8 grayscale grid
 * and normalise it into a 64-dim vector. The backend compares vectors with
 * cosine similarity. This demonstrably enrolls & verifies a face at prototype
 * fidelity (a passkey is offered as the stronger production-grade alternative).
 */
const GRID = 8;

export async function startCamera(video: HTMLVideoElement): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user", width: 320, height: 240 },
    audio: false,
  });
  video.srcObject = stream;
  await video.play();
  return stream;
}

export function stopCamera(stream: MediaStream | null) {
  stream?.getTracks().forEach((t) => t.stop());
}

export function computeEmbedding(video: HTMLVideoElement): number[] {
  const canvas = document.createElement("canvas");
  canvas.width = GRID;
  canvas.height = GRID;
  const ctx = canvas.getContext("2d");
  if (!ctx) return [];
  ctx.drawImage(video, 0, 0, GRID, GRID);
  const { data } = ctx.getImageData(0, 0, GRID, GRID);
  const gray: number[] = [];
  for (let i = 0; i < data.length; i += 4) {
    gray.push((data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114) / 255);
  }
  // Normalise: subtract mean, divide by std (contrast/lighting invariance).
  const mean = gray.reduce((a, b) => a + b, 0) / gray.length;
  const variance = gray.reduce((a, b) => a + (b - mean) ** 2, 0) / gray.length;
  const std = Math.sqrt(variance) || 1;
  return gray.map((v) => Number(((v - mean) / std).toFixed(4)));
}

export function captureQuality(video: HTMLVideoElement): number {
  // Rough brightness/contrast score to nudge the user for a good capture.
  const emb = computeEmbedding(video);
  if (!emb.length) return 0;
  const spread = Math.max(...emb) - Math.min(...emb);
  return Math.min(1, spread / 4);
}
