import { RiskFactor } from "@/lib/api";
import { AlertTriangle, CheckCircle2, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export function RiskFactors({ factors }: { factors: RiskFactor[] }) {
  if (!factors?.length) return null;
  return (
    <div className="space-y-2">
      {factors.map((f, i) => {
        const positive = f.points > 0;
        return (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 px-3 py-2"
          >
            <div className="flex items-center gap-2.5">
              {positive ? (
                <AlertTriangle className="h-4 w-4 shrink-0 text-risk-high" />
              ) : (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-risk-safe" />
              )}
              <div>
                <div className="text-sm font-medium capitalize">{f.name.replace(/_/g, " ")}</div>
                <div className="text-xs text-muted-foreground">{f.detail}</div>
              </div>
            </div>
            <div
              className={cn(
                "flex items-center gap-1 rounded-md px-2 py-0.5 text-sm font-semibold tabular-nums",
                positive ? "bg-risk-high/15 text-risk-high" : "bg-risk-safe/15 text-risk-safe"
              )}
            >
              {positive ? `+${f.points}` : <Minus className="h-3 w-3" />}
            </div>
          </div>
        );
      })}
    </div>
  );
}
