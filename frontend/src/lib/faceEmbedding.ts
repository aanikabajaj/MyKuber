/**
 * Prototype face embedding.
 *
 * Robustness improvements over a naive full-frame hash:
 *  1. Center-crop to the middle square of the frame — the face region — so the
 *     background contributes almost nothing to the vector.
 *  2. Downscale to a 12x12 grayscale grid (144 features) — enough structure to
 *     tell faces apart, coarse enough to tolerate small pose/expression shifts.
 *  3. Per-frame mean/std normalisation — lighting/contrast invariance.
 *  4. Multi-frame averaging (see captureAveragedEmbedding) — the enrolled and
 *     verified templates are each an average of ~10 frames, which cancels out
 *     momentary jitter (blinking, micro-movements) and makes matching stable.
 *
 * The backend compares templates with cosine similarity. This is an honest
 * prototype of biometric matching; a WebAuthn passkey is offered as the
 * stronger production-grade alternative.
 */
const GRID = 12;
const CROP = 0.7; // fraction of the shorter side used for the central square

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function startCamera(video: HTMLVideoElement): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user", width: 640, height: 480 },
    audio: false,
  });
  video.srcObject = stream;
  await video.play();
  return stream;
}

export function stopCamera(stream: MediaStream | null) {
  stream?.getTracks().forEach((t) => t.stop());
}

/** One normalised, center-cropped grayscale frame vector (length 144). */
function frameEmbedding(video: HTMLVideoElement): number[] {
  const vw = video.videoWidth || 640;
  const vh = video.videoHeight || 480;
  if (!vw || !vh) return [];

  const side = Math.min(vw, vh) * CROP;
  const sx = (vw - side) / 2;
  const sy = (vh - side) / 2;

  const canvas = document.createElement("canvas");
  canvas.width = GRID;
  canvas.height = GRID;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return [];
  // Draw only the central square region, scaled down to GRIDxGRID.
  ctx.drawImage(video, sx, sy, side, side, 0, 0, GRID, GRID);

  const { data } = ctx.getImageData(0, 0, GRID, GRID);
  const gray: number[] = [];
  for (let i = 0; i < data.length; i += 4) {
    gray.push((data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114) / 255);
  }
  const mean = gray.reduce((a, b) => a + b, 0) / gray.length;
  const variance = gray.reduce((a, b) => a + (b - mean) ** 2, 0) / gray.length;
  const std = Math.sqrt(variance) || 1;
  return gray.map((v) => (v - mean) / std);
}

/** Single-frame embedding (kept for compatibility). */
export function computeEmbedding(video: HTMLVideoElement): number[] {
  return frameEmbedding(video).map((v) => Number(v.toFixed(4)));
}

/**
 * Capture several frames over ~1 second and return their averaged embedding.
 * Used for BOTH enrollment and verification so the two templates are directly
 * comparable and resistant to momentary variation.
 */
export async function captureAveragedEmbedding(
  video: HTMLVideoElement,
  frames = 10,
  gapMs = 100,
  onProgress?: (p: number) => void
): Promise<number[]> {
  const acc: number[][] = [];
  for (let i = 0; i < frames; i++) {
    const e = frameEmbedding(video);
    if (e.length) acc.push(e);
    onProgress?.((i + 1) / frames);
    await sleep(gapMs);
  }
  if (!acc.length) return [];
  const dim = acc[0].length;
  const avg = new Array(dim).fill(0);
  for (const e of acc) for (let j = 0; j < dim; j++) avg[j] += e[j];
  return avg.map((v) => Number((v / acc.length).toFixed(4)));
}

/**
 * iPhone-Face-ID-style guided enrollment: sample many single frames while the
 * user slowly moves their head, producing a SET of angle templates. At login
 * the candidate is matched against the best of these, so any pose is accepted.
 */
export async function captureMultiAngle(
  video: HTMLVideoElement,
  samples = 18,
  totalMs = 5000,
  onProgress?: (p: number) => void
): Promise<number[][]> {
  const out: number[][] = [];
  const gap = Math.max(60, Math.floor(totalMs / samples));
  for (let i = 0; i < samples; i++) {
    const e = frameEmbedding(video);
    if (e.length) out.push(e.map((v) => Number(v.toFixed(4))));
    onProgress?.((i + 1) / samples);
    await sleep(gap);
  }
  return out;
}
