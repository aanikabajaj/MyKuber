import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva("relative w-full rounded-lg border p-4 text-sm flex gap-3", {
  variants: {
    variant: {
      default: "border-border bg-card",
      info: "border-primary/30 bg-primary/10 text-foreground",
      success: "border-risk-safe/30 bg-risk-safe/10 text-foreground",
      warning: "border-risk-medium/30 bg-risk-medium/10 text-foreground",
      destructive: "border-risk-critical/30 bg-risk-critical/10 text-foreground",
    },
  },
  defaultVariants: { variant: "default" },
});

export function Alert({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>) {
  return <div className={cn(alertVariants({ variant }), className)} {...props} />;
}

export function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h5 className={cn("mb-1 font-semibold leading-none", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("text-sm text-muted-foreground", className)} {...props} />;
}
