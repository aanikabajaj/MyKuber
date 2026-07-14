import { Check } from "lucide-react";
import { cn, STEP_LABELS } from "@/lib/utils";

export function StepIndicator({
  steps,
  completed,
  current,
}: {
  steps: string[];
  completed: string[];
  current: string | null;
}) {
  const allSteps = ["password", ...steps];
  const done = new Set(["password", ...completed]);
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {allSteps.map((s, i) => {
        const isDone = done.has(s);
        const isCurrent = s === current;
        return (
          <div key={s} className="flex items-center gap-1.5">
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                isDone
                  ? "border-risk-safe/40 bg-risk-safe/15 text-risk-safe"
                  : isCurrent
                  ? "border-primary bg-primary/15 text-primary animate-pulse-ring"
                  : "border-border bg-secondary/40 text-muted-foreground"
              )}
            >
              {isDone ? <Check className="h-3 w-3" /> : <span className="tabular-nums">{i + 1}</span>}
              {s === "password" ? "Password" : STEP_LABELS[s] || s}
            </div>
            {i < allSteps.length - 1 && <div className="h-px w-3 bg-border" />}
          </div>
        );
      })}
    </div>
  );
}
