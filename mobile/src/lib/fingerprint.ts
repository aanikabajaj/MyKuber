import { Platform } from "react-native";
import { getItem, setItem } from "./storage";

function randHex(n: number): string {
  const c = "0123456789abcdef";
  let s = "";
  for (let i = 0; i < n; i++) s += c[Math.floor(Math.random() * 16)];
  return s;
}

export interface DeviceInfo {
  fingerprint: string;
  browser: string;
  os: string;
  timezone: string;
  language: string;
  screen_resolution: string;
  user_agent: string;
}

let cached: DeviceInfo | null = null;

export async function getDeviceInfo(): Promise<DeviceInfo> {
  if (cached) return cached;
  let fp = await getItem("iaare_device_fp");
  if (!fp) {
    fp = randHex(40);
    await setItem("iaare_device_fp", fp);
  }
  let tz = "unknown";
  try {
    tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown";
  } catch {}
  cached = {
    fingerprint: fp,
    browser: `IAARE Mobile (${Platform.OS})`,
    os: Platform.OS === "ios" ? "iOS" : Platform.OS === "android" ? "Android" : "Web",
    timezone: tz,
    language: "en",
    screen_resolution: "mobile",
    user_agent: `IAARE-Mobile/${Platform.OS}`,
  };
  return cached;
}
