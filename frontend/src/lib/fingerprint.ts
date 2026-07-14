/** Lightweight, self-contained browser fingerprint (no external library). */

async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function canvasSignature(): string {
  try {
    const canvas = document.createElement("canvas");
    canvas.width = 240;
    canvas.height = 60;
    const ctx = canvas.getContext("2d");
    if (!ctx) return "no-canvas";
    ctx.textBaseline = "top";
    ctx.font = "16px 'Arial'";
    ctx.fillStyle = "#f60";
    ctx.fillRect(10, 10, 120, 30);
    ctx.fillStyle = "#069";
    ctx.fillText("IAARE-PSB-\u{1F6E1}", 15, 15);
    ctx.strokeStyle = "rgba(120,60,200,0.6)";
    ctx.beginPath();
    ctx.arc(80, 30, 20, 0, Math.PI * 2);
    ctx.stroke();
    return canvas.toDataURL();
  } catch {
    return "canvas-error";
  }
}

export interface DeviceInfo {
  fingerprint: string;
  browser: string;
  os: string;
  timezone: string;
  language: string;
  screen_resolution: string;
  user_agent: string;
  label?: string;
}

function detectBrowser(ua: string): string {
  if (/edg/i.test(ua)) return "Microsoft Edge";
  if (/chrome|crios/i.test(ua)) return "Google Chrome";
  if (/firefox|fxios/i.test(ua)) return "Mozilla Firefox";
  if (/safari/i.test(ua)) return "Safari";
  return "Unknown Browser";
}

function detectOS(ua: string): string {
  if (/windows/i.test(ua)) return "Windows";
  if (/android/i.test(ua)) return "Android";
  if (/iphone|ipad|ipod/i.test(ua)) return "iOS";
  if (/mac os x/i.test(ua)) return "macOS";
  if (/linux/i.test(ua)) return "Linux";
  return "Unknown OS";
}

let cached: DeviceInfo | null = null;

export async function getDeviceInfo(): Promise<DeviceInfo> {
  if (cached) return cached;
  const ua = navigator.userAgent;
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown";
  const res = `${window.screen.width}x${window.screen.height}`;
  const parts = [
    ua,
    navigator.language,
    tz,
    res,
    String(navigator.hardwareConcurrency || 0),
    String((navigator as any).deviceMemory || 0),
    canvasSignature(),
  ].join("|");
  const fingerprint = (await sha256Hex(parts)).slice(0, 40);
  cached = {
    fingerprint,
    browser: detectBrowser(ua),
    os: detectOS(ua),
    timezone: tz,
    language: navigator.language,
    screen_resolution: res,
    user_agent: ua,
  };
  return cached;
}
