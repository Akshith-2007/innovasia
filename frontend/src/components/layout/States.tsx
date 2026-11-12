import { AlertTriangle, Database, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/card";
import { ApiError } from "@/services/api";
import type { SourceInfo } from "@/types/api";
import { cn, formatDate } from "@/lib/utils";

export function PageLoading() {
  return (
    <div className="flex min-h-[60svh] items-center justify-center" role="status" aria-live="polite">
      <Loader2 className="size-6 animate-spin text-forest" aria-hidden />
      <span className="sr-only">Loading page</span>
    </div>
  );
}

export function LoadingBlock({ label = "Loading", className }: { label?: string; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={cn("flex min-h-40 items-center justify-center gap-3 text-sm text-muted", className)}>
      <Loader2 className="size-4 animate-spin" aria-hidden /> {label}…
    </div>
  );
}

const HINTS: Record<string, string> = {
  network: "Start the backend with ./dev.sh, then retry.",
  data_unavailable:
    "Official data has not been imported yet. See README → Data acquisition (import the official CSV, then preprocess).",
  model_unavailable: "No model has been trained yet. See README → Model training.",
  insufficient_data: "This selection does not have enough history for a reliable result.",
  ambiguous_series: "Pick one variety and grade above; prices differ between them.",
  not_found: "No official observations match this selection.",
  rate_limited: "Too many requests in a short time. Wait a minute and try again.",
};

export function ErrorState({ error, title, className }: { error: unknown; title?: string; className?: string }) {
  const e = error instanceof ApiError ? error : null;
  const code = e?.code ?? "unknown";
  return (
    <div role="alert" className={cn("rounded-2xl border border-danger/25 bg-danger/5 p-5 text-sm", className)}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden />
        <div className="min-w-0 space-y-1">
          <p className="font-semibold text-charcoal">{title ?? "Unable to load data"}</p>
          <p className="text-ink">{e?.message ?? String(error)}</p>
          {HINTS[code] ? <p className="text-muted">{HINTS[code]}</p> : null}
          {code !== "unknown" ? <p className="font-mono text-xs text-muted">code: {code}</p> : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("flex min-h-40 flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-line p-6 text-center text-sm text-muted", className)}>
      <Database className="size-5 text-sage" aria-hidden />
      {children}
    </div>
  );
}

export function SourceNote({ source, className }: { source?: SourceInfo | null; className?: string }) {
  if (!source) return null;
  const range = source.observation_range;
  return (
    <div className={cn("flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted", className)}>
      {source.live ? (
        <Badge tone="live">Live · data.gov.in</Badge>
      ) : source.third_party ? (
        <Badge tone="concept">Kaggle mirror of AGMARKNET</Badge>
      ) : (
        <Badge tone="cached">Stored official data</Badge>
      )}
      <span>{source.name}</span>
      {source.licence ? <span>Licence: {source.licence.split(",")[0]}</span> : null}
      {range ? (
        <span>
          Observations {formatDate(range[0])}
          {range[1] && range[1] !== range[0] ? ` – ${formatDate(range[1])}` : ""}
        </span>
      ) : null}
      {source.retrieved_at ? <span>Retrieved {formatDate(source.retrieved_at)}</span> : null}
      {source.resource_url ? (
        <a className="underline decoration-line underline-offset-2 hover:text-forest" href={source.resource_url} target="_blank" rel="noreferrer">
          Resource
        </a>
      ) : null}
    </div>
  );
}
