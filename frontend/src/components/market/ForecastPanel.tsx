import { useQuery } from "@tanstack/react-query";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { axisProps, chartColors, inrTick } from "@/components/charts/theme";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/layout/States";
import { Badge } from "@/components/ui/card";
import { type Selection, splitVariety, useHistory } from "@/hooks/useMarketData";
import { cn, formatDate, formatNumber, formatPrice } from "@/lib/utils";
import { api } from "@/services/api";

type Metrics = { mae: number; mape: number | null; directional_accuracy: number | null };
type Horizon = {
  horizon_days: number;
  available: boolean;
  reason?: string;
  target_date_window?: [string, string];
  modal_price?: number;
  interval?: { level: number; lower: number; upper: number; test_coverage: number } | null;
  beats_naive_on_test?: boolean;
  test_metrics_overall?: Metrics;
  test_metrics_series?: { selected: Metrics } | null;
};
type Horizons = {
  latest_observation: { date: string; modal_price: number };
  horizons: Horizon[];
  model_version: string;
  data_cutoff: string;
};

const DAY = 86_400_000;
const HISTORY_DAYS = 90;
const t = (iso: string) => new Date(`${iso}T00:00:00`).getTime();

/** Prices expected 7, 14 and 30 days after the latest observation, drawn after recent actual prices. */
export function ForecastPanel({ selection }: { selection: Selection }) {
  const ready = !!(selection.state && selection.market && selection.commodity);
  const fc = useQuery({
    queryKey: ["horizons", selection.state, selection.district, selection.market, selection.commodity, selection.varietyGrade],
    queryFn: () =>
      api.post<Horizons>("/decision/forecast-horizons", {
        state: selection.state,
        district: selection.district || null,
        market: selection.market,
        commodity: selection.commodity,
        ...splitVariety(selection.varietyGrade),
      }),
    enabled: ready,
    retry: false,
  });
  const history = useHistory(selection);

  if (!ready) return <EmptyState>Select a mandi and commodity to see prices forecast for the coming weeks.</EmptyState>;
  if (fc.isLoading) return <LoadingBlock label="Running forecasts" />;
  if (fc.isError) return <ErrorState error={fc.error} title="No forecast for this selection" />;
  const d = fc.data!.data;
  const latest = d.latest_observation;
  const ready_h = d.horizons.filter((h) => h.available);
  if (!ready_h.length) return <EmptyState>The current model has no multi-day forecasts yet.</EmptyState>;
  const daysOld = Math.round((Date.now() - t(latest.date)) / DAY);

  return (
    <div className="space-y-6" data-testid="forecast-result">
      {daysOld > 7 ? (
        <p className="rounded-xl bg-amber/10 px-4 py-3 text-sm text-amber-ink" role="status">
          The latest price for this series is from {formatDate(latest.date)} ({daysOld} days ago), so these forecasts start from then, not today.
          AGMARKNET renamed many mandis in Dec 2025; try the "… APMC" name of this market for current data.
        </p>
      ) : null}

      <div className="rounded-card border border-line bg-white p-4 md:p-6">
        <ForecastChart latest={latest} horizons={ready_h} history={history.data?.data ?? []} />
        <p className="mt-3 text-xs text-muted">
          Solid line: recorded modal prices (last {HISTORY_DAYS} days). Dashed line: forecast. Shaded: the {Math.round((ready_h[0].interval?.level ?? 0.8) * 100)}% range
          that held in testing.
        </p>
      </div>

      <ul className="grid gap-4 md:grid-cols-3">
        {d.horizons.map((h) => (
          <li key={h.horizon_days} className="rounded-card border border-line bg-white p-5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-charcoal">In {h.horizon_days} days</p>
              {h.available && h.beats_naive_on_test === false ? <Badge tone="concept">weak forecast</Badge> : null}
            </div>
            {!h.available ? (
              <p className="mt-3 text-sm text-muted">{h.reason ?? "Not available."}</p>
            ) : (
              <HorizonCard h={h} latest={latest.modal_price} />
            )}
          </li>
        ))}
      </ul>

      <p className="text-xs text-muted">
        Latest recorded price {formatPrice(latest.modal_price)} on {formatDate(latest.date)} · model {d.model_version} · data up to {formatDate(d.data_cutoff)}.
        Forecasts are estimates from past prices only; weather, arrivals and policy are not modelled.
      </p>
    </div>
  );
}

function HorizonCard({ h, latest }: { h: Horizon; latest: number }) {
  const change = ((h.modal_price! - latest) / latest) * 100;
  const err = h.test_metrics_series?.selected.mape ?? h.test_metrics_overall?.mape ?? null;
  return (
    <>
      <p className="mt-1 text-xs text-muted">
        around {formatDate(h.target_date_window![0])}
      </p>
      <p className="mt-3 font-display text-3xl tabular text-forest">{formatPrice(h.modal_price)}</p>
      <p className={cn("text-sm tabular", change > 0 ? "text-forest" : change < 0 ? "text-danger" : "text-muted")}>
        {change >= 0 ? "▲" : "▼"} {formatNumber(Math.abs(change), 1)}% vs latest
      </p>
      {h.interval ? (
        <p className="mt-2 text-xs text-muted">
          Likely {formatPrice(h.interval.lower)} – {formatPrice(h.interval.upper)}
        </p>
      ) : null}
      {err != null ? (
        <p className="mt-1 text-xs text-muted">
          Typical error {formatNumber(err, 1)}%{h.test_metrics_series ? " for this mandi" : " (all mandis)"} in testing
        </p>
      ) : null}
    </>
  );
}

function ForecastChart({
  latest,
  horizons,
  history,
}: {
  latest: { date: string; modal_price: number };
  horizons: Horizon[];
  history: { arrival_date: string; modal_price: number }[];
}) {
  const start = t(latest.date) - HISTORY_DAYS * DAY;
  const actual = history
    .filter((r) => t(r.arrival_date) >= start && t(r.arrival_date) <= t(latest.date))
    .map((r) => ({ x: t(r.arrival_date), actual: r.modal_price }));
  // The forecast line and band start at the latest recorded price so they join the actual line.
  const future = [
    { x: t(latest.date), forecast: latest.modal_price, band: [latest.modal_price, latest.modal_price] as [number, number] },
    ...horizons.map((h) => ({
      x: t(h.target_date_window![0]),
      forecast: h.modal_price!,
      band: h.interval ? ([h.interval.lower, h.interval.upper] as [number, number]) : undefined,
    })),
  ];
  const data = [...actual, ...future].sort((a, b) => a.x - b.x);
  return (
    <div className="h-80 w-full" role="img" aria-label={`Recorded prices for the last ${HISTORY_DAYS} days and forecasts for ${horizons.map((h) => h.horizon_days).join(", ")} days ahead`}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={chartColors.grid} vertical={false} />
          <XAxis
            dataKey="x"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v: number) => new Date(v).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
            minTickGap={40}
            {...axisProps}
          />
          <YAxis tickFormatter={inrTick} width={56} domain={["auto", "auto"]} {...axisProps} />
          <Tooltip
            labelFormatter={(v) => formatDate(new Date(Number(v)).toISOString().slice(0, 10))}
            formatter={(v, name) => (Array.isArray(v) ? [`${formatPrice(v[0] as number)} – ${formatPrice(v[1] as number)}`, "Likely range"] : [formatPrice(v as number), name])}
            contentStyle={{ borderRadius: 12, borderColor: chartColors.grid, fontSize: 13 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area dataKey="band" name="Likely range" stroke="none" fill={chartColors.band} fillOpacity={0.6} connectNulls isAnimationActive={false} />
          <Line dataKey="actual" name="Recorded price" stroke={chartColors.modal} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
          <Line dataKey="forecast" name="Forecast" stroke={chartColors.accent} strokeWidth={2} strokeDasharray="6 4" dot={{ r: 4 }} connectNulls isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
