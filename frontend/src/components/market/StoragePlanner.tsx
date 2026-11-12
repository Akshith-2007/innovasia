import { useMutation, useQuery } from "@tanstack/react-query";
import { Calculator } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { EmptyState, ErrorState, LoadingBlock } from "@/components/layout/States";
import { Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/field";
import { type Selection, splitVariety } from "@/hooks/useMarketData";
import { cn, formatDate, formatPrice } from "@/lib/utils";
import { api } from "@/services/api";

type Source = { title: string; url: string; year: string };
type Option = {
  id: string;
  name: string;
  description: string;
  suited: boolean;
  default_cost_per_quintal_per_month: number | null;
  default_loss_pct_per_30_days: number | null;
  default_max_days: number | null;
  notes: string | null;
  sources: Source[];
};
type Scenario = {
  days: number;
  possible?: boolean;
  reason?: string;
  price_per_quintal?: number;
  sellable_quintals?: number;
  storage_cost?: number;
  net_revenue?: number;
  net_revenue_low?: number | null;
  net_revenue_high?: number | null;
  profit?: number | null;
  break_even_price?: number | null;
  vs_sell_now?: number;
  forecast_beats_naive_on_test?: boolean;
  forecast_test_mape?: number | null;
  storage_life_unknown?: boolean;
};
type Plan = {
  latest_observation: { date: string; modal_price: number };
  sell_now: Scenario;
  scenarios: Scenario[];
  assumptions: string[];
  data_cutoff: string;
};

export function StoragePlanner({ selection }: { selection: Selection }) {
  const ready = !!(selection.state && selection.market && selection.commodity);
  const opts = useQuery({
    queryKey: ["storage-options", selection.commodity],
    queryFn: () => api.get<{ category: string; options: Option[] }>("/decision/storage-options", { commodity: selection.commodity }),
    enabled: ready,
  });
  const [form, setForm] = useState({ quantity: "", totalCost: "", transport: "", fee: "", option: "", cost: "", loss: "", maxDays: "" });
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));
  const options = opts.data?.data.options ?? [];
  const chosen = options.find((o) => o.id === form.option);

  // Prefill the editable defaults whenever the storage option (or commodity) changes.
  useEffect(() => {
    if (!chosen) return;
    setForm((f) => ({
      ...f,
      cost: chosen.default_cost_per_quintal_per_month == null ? "" : String(chosen.default_cost_per_quintal_per_month),
      loss: chosen.default_loss_pct_per_30_days == null ? "" : String(chosen.default_loss_pct_per_30_days),
      maxDays: chosen.default_max_days == null ? "" : String(chosen.default_max_days),
    }));
  }, [chosen]);

  const plan = useMutation({
    mutationFn: () =>
      api.post<Plan>("/decision/plan", {
        state: selection.state,
        district: selection.district || null,
        market: selection.market,
        commodity: selection.commodity,
        ...splitVariety(selection.varietyGrade),
        quantity_quintals: Number(form.quantity),
        total_cost: form.totalCost === "" ? null : Number(form.totalCost),
        transport_cost_per_quintal: form.transport === "" ? null : Number(form.transport),
        market_fee_pct: form.fee === "" ? null : Number(form.fee),
        storage_option: form.option,
        storage_cost_per_quintal_per_month: form.cost === "" ? null : Number(form.cost),
        loss_pct_per_30_days: form.loss === "" ? null : Number(form.loss),
        max_storage_days: form.maxDays === "" ? null : Number(form.maxDays),
      }),
  });
  const key = [selection.state, selection.market, selection.commodity, selection.varietyGrade].join("|");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => plan.reset(), [key]);

  if (!ready) return <EmptyState>Select a mandi and commodity to plan storage and sale.</EmptyState>;
  if (opts.isLoading) return <LoadingBlock label="Loading storage options" />;
  if (opts.isError) return <ErrorState error={opts.error} />;

  const suited = options.filter((o) => o.suited);
  const other = options.filter((o) => !o.suited);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    plan.mutate();
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
      <form onSubmit={submit} className="space-y-5 rounded-card border border-line bg-white p-6" aria-label="Storage planner inputs">
        <div className="grid grid-cols-2 gap-4">
          <Num label="Quantity (quintals)" value={form.quantity} onChange={(v) => set({ quantity: v })} required min={0.01} />
          <Num label="Total cost of production (₹)" value={form.totalCost} onChange={(v) => set({ totalCost: v })} hint="Optional: enables profit and break-even" />
          <Num label="Transport to mandi (₹/quintal)" value={form.transport} onChange={(v) => set({ transport: v })} />
          <Num label="Commission + market fee (%)" value={form.fee} onChange={(v) => set({ fee: v })} max={50} />
        </div>
        <SelectField
          label="Storage option"
          placeholder="Choose how you would store"
          value={form.option}
          onChange={(v) => set({ option: v })}
          options={[
            ...suited.map((o) => ({ value: o.id, label: o.name })),
            ...other.map((o) => ({ value: o.id, label: `${o.name} (not usual for this crop)` })),
          ]}
          hint={`Crop type detected: ${opts.data!.data.category.replace("_", " ")}`}
        />
        {chosen ? (
          <div className="space-y-4 rounded-xl bg-paper p-4">
            <p className="text-sm text-ink">{chosen.description}</p>
            {chosen.id !== "sell_now" ? (
              <div className="grid grid-cols-3 gap-3">
                <Num label="Storage ₹/quintal/month" value={form.cost} onChange={(v) => set({ cost: v })} required placeholder="Enter yours" />
                <Num label="Loss % per 30 days" value={form.loss} onChange={(v) => set({ loss: v })} max={100} required placeholder="Enter yours" />
                <Num label="Keeps for (days)" value={form.maxDays} onChange={(v) => set({ maxDays: v })} placeholder="Unknown" />
              </div>
            ) : null}
            {chosen.notes ? <p className="text-xs text-muted">{chosen.notes}</p> : null}
            {chosen.id !== "sell_now" && chosen.default_cost_per_quintal_per_month == null ? (
              <p className="text-xs text-amber-ink">No published storage rent was found for this option and crop. Enter your local rate.</p>
            ) : null}
            {chosen.id !== "sell_now" && chosen.default_loss_pct_per_30_days == null ? (
              <p className="text-xs text-amber-ink">No published loss figure was found for this option and crop. Enter your own estimate.</p>
            ) : null}
            {chosen.sources.length ? (
              <ul className="space-y-1 text-xs text-muted">
                {chosen.sources.map((s) => (
                  <li key={s.url}>
                    Source:{" "}
                    <a className="underline underline-offset-2 hover:text-forest" href={s.url} target="_blank" rel="noreferrer">
                      {s.title}
                    </a>{" "}
                    ({s.year})
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        <Button type="submit" disabled={!form.option || !form.quantity || plan.isPending} className="w-full">
          <Calculator /> {plan.isPending ? "Calculating…" : "Compare sell now vs store"}
        </Button>
      </form>

      <div>
        {plan.isError ? <ErrorState error={plan.error} title="Could not build the plan" /> : null}
        {plan.data ? <PlanResult plan={plan.data.data} hasCost={form.totalCost !== ""} /> : !plan.isError ? (
          <EmptyState>Enter your numbers and choose a storage option to compare outcomes.</EmptyState>
        ) : null}
      </div>
    </div>
  );
}

function PlanResult({ plan, hasCost }: { plan: Plan; hasCost: boolean }) {
  const rows = [plan.sell_now, ...plan.scenarios];
  const best = plan.scenarios.filter((s) => s.possible && (s.vs_sell_now ?? 0) > 0).sort((a, b) => (b.vs_sell_now ?? 0) - (a.vs_sell_now ?? 0))[0];
  return (
    <div className="space-y-4" data-testid="plan-result">
      <p className="text-sm text-muted">
        Latest recorded price {formatPrice(plan.latest_observation.modal_price)} on {formatDate(plan.latest_observation.date)}. Forecasts use data up to{" "}
        {formatDate(plan.data_cutoff)}.
      </p>
      <div className="overflow-x-auto rounded-card border border-line bg-white" tabIndex={0} role="region" aria-label="Sell now versus storing (scrolls horizontally)">
        <table className="w-full min-w-[620px] text-left text-sm">
          <thead className="border-b border-line bg-paper-deep text-xs tracking-wider text-muted uppercase">
            <tr>
              <th className="px-4 py-3">When</th>
              <th className="px-4 py-3 text-right">Price/q</th>
              <th className="px-4 py-3 text-right">You receive</th>
              <th className="px-4 py-3 text-right">Likely range</th>
              <th className="px-4 py-3 text-right">vs sell now</th>
              {hasCost ? <th className="px-4 py-3 text-right">Profit</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.days} className={cn("border-b border-line/60 last:border-0", s === best && "bg-sage-soft/60")}>
                <td className="px-4 py-3 font-medium">
                  {s.days === 0 ? "Sell now" : `Store ${s.days} days`}
                  {s.possible && s.forecast_beats_naive_on_test === false ? <Badge tone="concept" className="ml-2">weak forecast</Badge> : null}
                </td>
                {s.days > 0 && !s.possible ? (
                  <td className="px-4 py-3 text-muted" colSpan={hasCost ? 5 : 4}>
                    {s.reason}
                  </td>
                ) : (
                  <>
                    <td className="px-4 py-3 text-right tabular">{formatPrice(s.price_per_quintal)}</td>
                    <td className="px-4 py-3 text-right tabular font-semibold">{formatPrice(s.net_revenue)}</td>
                    <td className="px-4 py-3 text-right tabular text-muted">
                      {s.net_revenue_low != null && s.net_revenue_high != null ? `${formatPrice(s.net_revenue_low)} – ${formatPrice(s.net_revenue_high)}` : "—"}
                    </td>
                    <td className={cn("px-4 py-3 text-right tabular", (s.vs_sell_now ?? 0) > 0 ? "text-forest" : (s.vs_sell_now ?? 0) < 0 ? "text-danger" : "")}>
                      {s.days === 0 ? "—" : `${(s.vs_sell_now ?? 0) >= 0 ? "+" : "−"}${formatPrice(Math.abs(s.vs_sell_now ?? 0))}`}
                    </td>
                    {hasCost ? <td className="px-4 py-3 text-right tabular">{s.profit == null ? "—" : `${s.profit < 0 ? "−" : ""}${formatPrice(Math.abs(s.profit))}`}</td> : null}
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-sm">
        {best ? (
          <>
            Storing <strong>{best.days} days</strong> is expected to earn <strong>{formatPrice(best.vs_sell_now)}</strong> more than selling now after storage, losses and fees
            {best.net_revenue_low != null && best.net_revenue_low < plan.sell_now.net_revenue! ? ", but the low end of the range is below selling now" : ""}.
          </>
        ) : plan.scenarios.length === 0 ? (
          <>Store-later forecasts are not available from the current model yet, so only selling now can be shown.</>
        ) : !plan.scenarios.some((s) => s.possible) ? (
          <>None of the forecast periods fit this storage option (see the reasons above).</>
        ) : (
          <>Based on the forecasts and your costs, storing is not expected to beat selling now.</>
        )}
        {plan.sell_now.break_even_price != null ? ` Break-even price today: ${formatPrice(plan.sell_now.break_even_price)}/quintal.` : ""}
      </p>
      <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
        {plan.assumptions.map((a) => (
          <li key={a}>{a}</li>
        ))}
        <li>“Weak forecast” means that horizon's model did not beat “price stays the same” in testing.</li>
      </ul>
    </div>
  );
}

function Num({
  label,
  value,
  onChange,
  hint,
  required,
  min = 0,
  max,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
  required?: boolean;
  min?: number;
  max?: number;
  placeholder?: string;
}) {
  const id = `sp-${label.replace(/\W+/g, "-")}`;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      <input
        id={id}
        type="number"
        inputMode="decimal"
        step="any"
        min={min}
        max={max}
        required={required}
        placeholder={placeholder}
        className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint ? <p className="text-[0.7rem] text-muted">{hint}</p> : null}
    </div>
  );
}

