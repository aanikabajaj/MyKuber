import React, { useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { AppButton, Muted } from "./ui";
import { colors, radius } from "../theme";

/**
 * Camera face-scan (mirrors the web experience). In "enroll" mode it captures
 * several frames while the user moves their head; in "verify" mode a single
 * frame. Frames are sent as base64 to the backend, which computes the embedding
 * with Pillow and matches it — so behaviour is identical to the web client.
 */
export function FaceScanner({
  mode,
  onDone,
  busy,
}: {
  mode: "enroll" | "verify";
  onDone: (images: string[]) => void;
  busy?: boolean;
}) {
  const [permission, requestPermission] = useCameraPermissions();
  const camRef = useRef<CameraView>(null);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [hint, setHint] = useState("");

  if (!permission) {
    return <Muted>Loading camera…</Muted>;
  }
  if (!permission.granted) {
    return (
      <View style={{ gap: 12, alignItems: "center" }}>
        <Muted>Camera access is needed for face verification.</Muted>
        <AppButton title="Grant camera access" onPress={requestPermission} />
      </View>
    );
  }

  const PROMPTS = [
    "Look straight ahead",
    "Slowly turn your head left",
    "Now turn to the right",
    "Tilt your head up a little",
    "Tilt down a little",
    "Look straight again",
    "Almost there…",
    "Hold still",
  ];

  async function capture() {
    if (!camRef.current || scanning) return;
    setScanning(true);
    setProgress(0);
    const shots: string[] = [];
    const count = mode === "enroll" ? 8 : 1;
    try {
      for (let i = 0; i < count; i++) {
        if (mode === "enroll") setHint(PROMPTS[i % PROMPTS.length]);
        const pic = await camRef.current.takePictureAsync({
          base64: true,
          quality: 0.5,
          skipProcessing: true,
        });
        if (pic?.base64) shots.push(pic.base64);
        setProgress((i + 1) / count);
        if (count > 1) await new Promise((r) => setTimeout(r, 650));
      }
      if (shots.length) onDone(shots);
    } finally {
      setScanning(false);
      setHint("");
    }
  }

  const pct = Math.round(progress * 100);
  return (
    <View style={{ alignItems: "center", gap: 12 }}>
      <View style={styles.frame}>
        <CameraView ref={camRef} style={StyleSheet.absoluteFill} facing="front" />
        <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.center]}>
          <View
            style={[
              styles.oval,
              { borderColor: scanning ? colors.safe : colors.primary },
            ]}
          />
        </View>
        {scanning && (
          <View style={styles.progressWrap}>
            <View style={styles.progressTrack}>
              <View style={[styles.progressBar, { width: `${pct}%` }]} />
            </View>
          </View>
        )}
      </View>
      <Muted style={{ textAlign: "center" }}>
        {scanning
          ? mode === "enroll" && hint
            ? `${hint}  (${pct}%)`
            : `Hold still… ${pct}%`
          : mode === "enroll"
          ? "Position your face, then slowly rotate your head as it scans all angles."
          : "Center your face in the oval and tap Scan."}
      </Muted>
      <AppButton
        title={scanning ? "Scanning…" : mode === "enroll" ? "Start Face Scan" : "Scan Face"}
        onPress={capture}
        loading={busy || scanning}
        variant="accent"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { width: 240, height: 300, borderRadius: radius.lg, overflow: "hidden", backgroundColor: "#000", borderWidth: 1, borderColor: colors.cardBorder },
  center: { alignItems: "center", justifyContent: "center" },
  oval: { width: 160, height: 210, borderRadius: 110, borderWidth: 3, borderStyle: "dashed" },
  progressWrap: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 10, backgroundColor: "rgba(0,0,0,0.55)" },
  progressTrack: { height: 6, borderRadius: 3, backgroundColor: "rgba(255,255,255,0.25)", overflow: "hidden" },
  progressBar: { height: 6, borderRadius: 3, backgroundColor: colors.safe },
});
