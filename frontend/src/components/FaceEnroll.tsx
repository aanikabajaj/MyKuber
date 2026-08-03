import { useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, ScanFace, VideoOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { captureMultiAngle, startCamera, stopCamera } from "@/lib/faceEmbedding";

const RING_R = 96;
const RING_C = 2 * Math.PI * RING_R;

/**
 * Guided multi-angle face enrollment (iPhone Face ID style). The user slowly
 * moves their head in a circle while ~18 angle templates are captured; a dial
 * fills to show progress. The captured set is passed to `onEnroll`.
 */
export function FaceEnroll({
  onEnroll,
  busy,
}: {
  onEnroll: (embeddings: number[][]) => void;
  busy?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [captured, setCaptured] = useState(0);

  async function begin() {
    setError("");
    try {
      if (videoRef.current) {
        streamRef.current = await startCamera(videoRef.current);
        setActive(true);
      }
    } catch {
      setError("Camera access was denied or is unavailable. You can retry or use a passkey instead.");
    }
  }

  useEffect(() => {
    begin();
    return () => stopCamera(streamRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startEnroll() {
    if (!videoRef.current || scanning) return;
    setScanning(true);
    setProgress(0);
    setCaptured(0);
    try {
      const templates = await captureMultiAngle(videoRef.current, 18, 5200, setProgress);
      setCaptured(templates.length);
      if (templates.length) onEnroll(templates);
    } finally {
      setScanning(false);
    }
  }

  const pct = Math.round(progress * 100);
  const done = captured > 0 && !scanning;

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative aspect-square w-full max-w-xs">
        <div className="absolute inset-0 overflow-hidden rounded-full border border-border bg-black">
          <video ref={videoRef} playsInline muted className="h-full w-full object-cover" />
          {!active && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-foreground">
              <VideoOff className="h-8 w-8" />
              <span className="text-xs">Camera inactive</span>
            </div>
          )}
        </div>

        {/* progress dial */}
        <svg viewBox="0 0 220 220" className="absolute inset-0 h-full w-full -rotate-90">
          <circle cx="110" cy="110" r={RING_R} fill="none" stroke="hsl(var(--secondary))" strokeWidth="7" />
          <circle
            cx="110"
            cy="110"
            r={RING_R}
            fill="none"
            stroke={done ? "hsl(var(--risk-safe))" : "hsl(var(--primary))"}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={RING_C}
            strokeDashoffset={RING_C * (1 - progress)}
            style={{ transition: "stroke-dashoffset 0.15s linear" }}
          />
        </svg>

        {active && (
          <div className="absolute left-1/2 top-3 -translate-x-1/2 rounded-full bg-black/50 px-2 py-1 text-xs text-risk-safe">
            <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-risk-safe align-middle" />
            {scanning ? `Scanning ${pct}%` : done ? "Complete" : "Live"}
          </div>
        )}
        {done && (
          <div className="absolute inset-0 flex items-center justify-center">
            <CheckCircle2 className="h-16 w-16 text-risk-safe drop-shadow-lg animate-scale-in" />
          </div>
        )}
      </div>

      <p className="max-w-xs text-center text-xs text-muted-foreground">
        {scanning
          ? "Keep moving — slowly turn your head left, right, up and down."
          : done
          ? `Captured ${captured} angles of your face.`
          : "Position your face in the circle, then slowly move your head in a circle while it scans."}
      </p>
      {error && <p className="max-w-xs text-center text-xs text-risk-high">{error}</p>}

      <div className="flex gap-2">
        {!active ? (
          <Button variant="outline" onClick={begin} type="button">
            <Camera className="h-4 w-4" /> Enable Camera
          </Button>
        ) : (
          <Button onClick={startEnroll} loading={busy || scanning} type="button">
            <ScanFace className="h-4 w-4" />
            {scanning ? "Scanning…" : done ? "Re-scan" : "Start Face Enrollment"}
          </Button>
        )}
      </div>
    </div>
  );
}
