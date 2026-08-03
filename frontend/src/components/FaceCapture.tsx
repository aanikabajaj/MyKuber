import { useEffect, useRef, useState } from "react";
import { Camera, ScanFace, VideoOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { captureAveragedEmbedding, startCamera, stopCamera } from "@/lib/faceEmbedding";

export function FaceCapture({
  onCapture,
  label = "Capture & Verify",
  busy,
}: {
  onCapture: (embedding: number[]) => void;
  label?: string;
  busy?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string>("");
  const [capturing, setCapturing] = useState(false);
  const [progress, setProgress] = useState(0);

  async function begin() {
    setError("");
    try {
      if (videoRef.current) {
        streamRef.current = await startCamera(videoRef.current);
        setActive(true);
      }
    } catch (e: any) {
      setError("Camera access was denied or is unavailable. You can retry or use a passkey instead.");
    }
  }

  useEffect(() => {
    begin();
    return () => stopCamera(streamRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function capture() {
    if (!videoRef.current || capturing) return;
    setCapturing(true);
    setProgress(0);
    try {
      // Average ~10 frames over ~1s so blinking / small movements don't matter.
      const emb = await captureAveragedEmbedding(videoRef.current, 10, 100, setProgress);
      if (emb.length) onCapture(emb);
    } finally {
      setCapturing(false);
      setProgress(0);
    }
  }

  const pct = Math.round(progress * 100);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative aspect-[4/3] w-full max-w-sm overflow-hidden rounded-xl border border-border bg-black">
        <video ref={videoRef} playsInline muted className="h-full w-full object-cover" />
        {active && (
          <>
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div
                className={`h-44 w-36 rounded-[45%] border-2 border-dashed transition-colors ${
                  capturing ? "border-risk-safe" : "border-primary/70 animate-pulse-ring"
                }`}
              />
            </div>
            <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-black/50 px-2 py-1 text-xs text-risk-safe">
              <span className="h-2 w-2 animate-pulse rounded-full bg-risk-safe" /> Live
            </div>
            {capturing && (
              <div className="absolute inset-x-0 bottom-0 bg-black/60 p-2">
                <div className="mb-1 text-center text-xs text-white">Hold still… {pct}%</div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/20">
                  <div
                    className="h-full rounded-full bg-risk-safe transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )}
          </>
        )}
        {!active && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <VideoOff className="h-8 w-8" />
            <span className="text-xs">Camera inactive</span>
          </div>
        )}
      </div>

      <p className="max-w-sm text-center text-xs text-muted-foreground">
        Center your face in the oval, face the light, and hold still while it scans.
      </p>
      {error && <p className="max-w-sm text-center text-xs text-risk-high">{error}</p>}

      <div className="flex gap-2">
        {!active ? (
          <Button variant="outline" onClick={begin} type="button">
            <Camera className="h-4 w-4" /> Enable Camera
          </Button>
        ) : (
          <Button onClick={capture} loading={busy || capturing} type="button">
            <ScanFace className="h-4 w-4" /> {capturing ? "Scanning…" : label}
          </Button>
        )}
      </div>
    </div>
  );
}
