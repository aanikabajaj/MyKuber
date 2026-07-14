import { useEffect, useRef, useState } from "react";
import { Camera, ScanFace, VideoOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { computeEmbedding, startCamera, stopCamera } from "@/lib/faceEmbedding";

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

  function capture() {
    if (!videoRef.current) return;
    const emb = computeEmbedding(videoRef.current);
    if (emb.length) onCapture(emb);
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative aspect-[4/3] w-full max-w-sm overflow-hidden rounded-xl border border-border bg-black">
        <video ref={videoRef} playsInline muted className="h-full w-full object-cover" />
        {active && (
          <>
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="h-40 w-32 rounded-[45%] border-2 border-dashed border-primary/70 animate-pulse-ring" />
            </div>
            <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-black/50 px-2 py-1 text-xs text-risk-safe">
              <span className="h-2 w-2 animate-pulse rounded-full bg-risk-safe" /> Live
            </div>
          </>
        )}
        {!active && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <VideoOff className="h-8 w-8" />
            <span className="text-xs">Camera inactive</span>
          </div>
        )}
      </div>

      {error && <p className="max-w-sm text-center text-xs text-risk-high">{error}</p>}

      <div className="flex gap-2">
        {!active ? (
          <Button variant="outline" onClick={begin} type="button">
            <Camera className="h-4 w-4" /> Enable Camera
          </Button>
        ) : (
          <Button onClick={capture} loading={busy} type="button">
            <ScanFace className="h-4 w-4" /> {label}
          </Button>
        )}
      </div>
    </div>
  );
}
