import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { EmptyState, ErrorState, LoadingBlock, SourceNote } from "@/components/layout/States";
import { formatDate, formatPrice } from "@/lib/utils";
import { api } from "@/services/api";
import type { PriceRecord } from "@/types/api";

/** Today's published prices for every mandi in the selected state (live from data.gov.in when available). */
export function StateLivePrices({ state }: { state: string }) {
  const [filter, setFilter] = useState("");
  const q = useQuery({
    queryKey: ["state-prices", state],
    queryFn: () => api.get<PriceRecord[]>("/market/prices", { state }),
    enabled: !!state,
    retry: false,
    refetchInterval: 15 * 60_000,
  });
  if (!state) return <EmptyState>Select a state to see today's prices across its mandis.</EmptyState>;
  if (q.isLoading) return <LoadingBlock label="Fetching today's prices" />;
  if (q.isError) return <ErrorState error={q.error} />;
  const env = q.data!;
  const f = filter.trim().toLowerCase();
  const rows = env.data.filter((r) => !f || `${r.market} ${r.commodity} ${r.district}`.toLowerCase().includes(f));
  const liveErr = env.meta.live_error;
  return (
    <div className="space-y-4">
      {liveErr && !env.source?.live ? (
        <p className="rounded-xl bg-amber/10 px-4 py-3 text-sm text-amber-ink" role="status">
          Live prices unavailable ({liveErr.message}). Showing the latest stored observation per mandi instead.
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex min-w-0 flex-1 flex-col gap-1 sm:max-w-xs">
          <span className="text-xs font-semibold text-muted">Search mandi or commodity</span>
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none"
          />
        </label>
        <p className="text-sm text-muted">
          {rows.length} of {env.data.length} prices
        </p>
      </div>
      {rows.length === 0 ? (
        <EmptyState>No prices match.</EmptyState>
      ) : (
        <div className="max-h-[28rem] overflow-auto rounded-card border border-line bg-white" tabIndex={0} role="region" aria-label="Prices across the state (scrollable)">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="sticky top-0 border-b border-line bg-paper-deep text-xs tracking-wider text-muted uppercase">
              <tr>
                <th className="px-4 py-3">Mandi</th>
                <th className="px-4 py-3">Commodity</th>
                <th className="px-4 py-3 text-right">Min</th>
                <th className="px-4 py-3 text-right">Modal</th>
                <th className="px-4 py-3 text-right">Max</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 300).map((r) => (
                <tr key={`${r.market}|${r.commodity}|${r.variety}|${r.grade}`} className="border-b border-line/60 last:border-0">
                  <td className="px-4 py-2.5">
                    <span className="font-medium">{r.market}</span>
                    <span className="block text-xs text-muted">{r.district}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    {r.commodity}
                    <span className="block text-xs text-muted">{[r.variety, r.grade].filter(Boolean).join(" · ")}</span>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular">{formatPrice(r.min_price)}</td>
                  <td className="px-4 py-2.5 text-right tabular font-semibold">{formatPrice(r.modal_price)}</td>
                  <td className="px-4 py-2.5 text-right tabular">{formatPrice(r.max_price)}</td>
                  <td className="px-4 py-2.5 whitespace-nowrap">{formatDate(r.arrival_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <SourceNote source={env.source} />
    </div>
  );
}
