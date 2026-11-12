import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("rounded-card border border-line bg-white/70 p-6", className)} {...props} />;
}

export function Badge({
  className,
  tone = "neutral",
  ...props
}: ComponentProps<"span"> & { tone?: "neutral" | "live" | "cached" | "concept" | "warn" }) {
  const tones = {
    neutral: "bg-paper-deep text-ink",
    live: "bg-forest text-paper",
    cached: "bg-sage-soft text-forest-deep",
    concept: "bg-amber/15 text-amber-ink",
    warn: "bg-danger/10 text-danger",
  } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.7rem] font-semibold uppercase tracking-wider",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
