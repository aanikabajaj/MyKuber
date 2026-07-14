import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function bandColor(band: string): string {
  switch (band) {
    case "SAFE":
      return "risk-safe";
    case "MEDIUM":
      return "risk-medium";
    case "HIGH":
      return "risk-high";
    case "CRITICAL":
      return "risk-critical";
    default:
      return "muted-foreground";
  }
}

export function bandHex(band: string): string {
  switch (band) {
    case "SAFE":
      return "#22c55e";
    case "MEDIUM":
      return "#eab308";
    case "HIGH":
      return "#f97316";
    case "CRITICAL":
      return "#ef4444";
    default:
      return "#64748b";
  }
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

export const STEP_LABELS: Record<string, string> = {
  mpin: "MPIN",
  second_factor: "Biometric / Passkey",
  email_otp: "Email OTP",
  sms_otp: "SMS OTP",
  totp: "Authenticator",
};
