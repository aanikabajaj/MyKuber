import { Platform } from "react-native";
import * as LocalAuthentication from "expo-local-authentication";

/**
 * Trigger the device's native biometric (Face ID / Touch ID / fingerprint).
 * On web or a device without enrolled biometrics we resolve true so the demo
 * flow can proceed (the backend still enforces the risk-based step for real
 * accounts). Returns whether the user was verified.
 */
export async function verifyBiometric(prompt = "Verify your identity"): Promise<boolean> {
  if (Platform.OS === "web") return true;
  try {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    if (!hasHardware || !enrolled) return true; // no biometric configured -> allow (demo)
    const res = await LocalAuthentication.authenticateAsync({
      promptMessage: prompt,
      cancelLabel: "Cancel",
      disableDeviceFallback: false,
    });
    return res.success;
  } catch {
    return false;
  }
}

export async function biometricLabel(): Promise<string> {
  if (Platform.OS === "web") return "Biometric";
  try {
    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
    if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) return "Face ID";
    if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) return "Fingerprint";
  } catch {}
  return "Biometric";
}

// Placeholder embedding sent to the backend after a successful native biometric
// (seeded demo accounts auto-pass; the native prompt is the real gate on device).
export const PLACEHOLDER_EMBEDDING = new Array(144).fill(0);
