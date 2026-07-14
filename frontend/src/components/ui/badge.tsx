import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/15 text-primary",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground",
        safe: "border-transparent bg-risk-safe/15 text-risk-safe",
        medium: "border-transparent bg-risk-medium/15 text-risk-medium",
        high: "border-transparent bg-risk-high/15 text-risk-high",
        critical: "border-transparent bg-risk-critical/15 text-risk-critical",
        success: "border-transparent bg-risk-safe/15 text-risk-safe",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export function bandVariant(band: string): BadgeProps["variant"] {
  return (
    { SAFE: "safe", MEDIUM: "medium", HIGH: "high", CRITICAL: "critical" } as const
  )[band] as BadgeProps["variant"] ?? "secondary";
}
