import { cn } from "@/lib/utils";

export function Logo({ light = false, className }: { light?: boolean; className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <svg viewBox="0 0 64 64" className="size-9" aria-hidden="true">
        <rect width="64" height="64" rx="14" className={light ? "fill-paper/15" : "fill-forest"} />
        <path
          d="M32 12c-9 8-13 16-13 23a13 13 0 0 0 26 0c0-7-4-15-13-23Z"
          fill="none"
          className="stroke-paper"
          strokeWidth="3.5"
          strokeLinejoin="round"
        />
        <path d="M32 26v22M25 36h14M27 42h10" className="stroke-amber-soft" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <span className="font-display text-lg leading-none font-semibold tracking-tight">
        Kisan Cold Link
      </span>
    </span>
  );
}
