import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className, compact }: { className?: string; compact?: boolean }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-purple-500 shadow-lg shadow-primary/30">
        <ShieldCheck className="h-5 w-5 text-white" />
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className="text-base font-bold tracking-tight">IAARE</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Punjab &amp; Sind Bank
          </div>
        </div>
      )}
    </div>
  );
}
