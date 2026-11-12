import { EmptyState, ErrorState, LoadingBlock, SourceNote } from "@/components/layout/States";
import { Badge } from "@/components/ui/card";
import { type Selection, useLatestPrices } from "@/hooks/useMarketData";
import { formatDate, formatPrice } from "@/lib/utils";

export function PriceCards({ selection }: { selection: Selection }) {
  const q = useLatestPrices(selection);
  if (!selection.commodity) return <EmptyState>Select a state, mandi and commodity to see published prices.</EmptyState>;
  if (q.isLoading) return <LoadingBlock label="Fetching official prices" />;
  if (q.isError) return <ErrorState error={q.error} />;
  const env = q.data!;
  const rows = env.data;
  if (!rows.length) return <EmptyState>No published prices for this selection.</EmptyState>;
  const liveErr = env.meta.live_error;

  return (
    <div className="space-y-4">
      {liveErr && !env.source?.live ? (
        <p className="rounded-xl bg-amber/10 px-4 py-3 text-sm text-amber-ink" role="status">
          Live data.gov.in prices unavailable ({liveErr.message}). Showing the latest stored observations instead (source labelled below).
        </p>
      ) : null}
      <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((r) => (
          <li key={`${r.market}-${r.variety}-${r.grade}-${r.arrival_date}`} className="rounded-card border border-line bg-white p-6" data-testid="price-card">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-charcoal">{r.commodity}</p>
                <p className="truncate text-xs text-muted">
                  {[r.variety, r.grade].filter(Boolean).join(" · ") || "Variety unspecified"}
                </p>
              </div>
              {env.source?.live ? (
                <Badge tone="live">Live</Badge>
              ) : r.source_kind === "third_party_mirror" ? (
                <Badge tone="concept">Kaggle mirror</Badge>
              ) : (
                <Badge tone="cached">Stored</Badge>
              )}
            </div>
            <p className="mt-6 text-xs font-semibold tracking-wider text-muted uppercase">Modal price</p>
            <p className="font-display text-4xl text-forest tabular">{formatPrice(r.modal_price)}</p>
            <p className="text-xs text-muted">per quintal</p>
            <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-line pt-4 text-sm">
              <div>
                <dt className="text-xs text-muted">Minimum</dt>
                <dd className="font-semibold tabular">{formatPrice(r.min_price)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Maximum</dt>
                <dd className="font-semibold tabular">{formatPrice(r.max_price)}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-muted">Market · observed</dt>
                <dd className="font-medium">
                  {r.market}, {r.district} · {formatDate(r.arrival_date)}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
      <SourceNote source={env.source} />
    </div>
  );
}
