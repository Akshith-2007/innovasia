import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin, Trash2, TrendingUp } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { EmptyState, ErrorState, LoadingBlock } from "@/components/layout/States";
import { Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/field";
import { cn, formatDate, formatNumber, formatPrice } from "@/lib/utils";
import { api } from "@/services/api";
import type { CommodityRow, VarietyRow } from "@/types/api";

type Settings = {
  storage_state: string | null;
  storage_district: string | null;
  transport_per_q_km: number | null;
  storage_rent_per_q_month: number | null;
  loss_pct_per_30_days: number | null;
  market_fee_pct: number | null;
  max_km: number | null;
  km_overrides: Record<string, number>;
};
type Lot = {
  id: string;
  farmer_name: string;
  village: string;
  commodity: string;
  variety: string | null;
  grade: string | null;
  quantity_q: number;
  entry_date: string;
};
type Option = {
  sell_after_days: number;
  sell_on: string;
  price_per_quintal: number;
  sellable_quintals: number;
  storage_cost: number;
  transport_cost: number;
  market_fee: number;
  total_selling_cost: number;
  net_revenue: number;
  net_revenue_low: number | null;
  net_revenue_high: number | null;
  forecast_beats_naive_on_test?: boolean;
  price_date?: string;
};
type MandiPlan = {
  state: string;
  district: string;
  market: string;
  variety: string;
  grade: string;
  km: number | null;
  km_source: "override" | "approx" | "unknown";
  latest_price_date: string;
  options: Option[];
  best: Option;
};
type Plan = {
  lot: Lot;
  days_in_storage_so_far: number;
  recommendation: (Option & { state: string; district: string; market: string; km: number | null; gain_vs_best_sell_now: number }) | null;
  mandis: MandiPlan[];
  skipped: { no_forecast: number; too_far: number };
  assumptions: string[];
};

export function FarmerPortal({ password }: { password: string }) {
  const headers = { "X-Admin-Password": password };
  const [openLot, setOpenLot] = useState<string | null>(null);
  return (
    <div className="space-y-8">
      <SettingsPanel headers={headers} />
      <LotsPanel headers={headers} openLot={openLot} onOpen={setOpenLot} />
      {openLot ? <PlanPanel key={openLot} lotId={openLot} headers={headers} /> : null}
    </div>
  );
}

function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="rounded-card border border-line bg-white p-6" aria-label={title}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function Num({ label, value, onChange, required, hint }: { label: string; value: string; onChange: (v: string) => void; required?: boolean; hint?: string }) {
  const id = `fp-${label.replace(/\W+/g, "-")}`;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      <input
        id={id}
        type="number"
        step="any"
        min={0}
        inputMode="decimal"
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none"
      />
      {hint ? <p className="text-[0.7rem] text-muted">{hint}</p> : null}
    </div>
  );
}

function Text({ label, value, onChange, required, type = "text" }: { label: string; value: string; onChange: (v: string) => void; required?: boolean; type?: string }) {
  const id = `fp-${label.replace(/\W+/g, "-")}`;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none"
      />
    </div>
  );
}

const str = (v: number | null | undefined) => (v == null ? "" : String(v));
const num = (v: string) => (v === "" ? null : Number(v));

function SettingsPanel({ headers }: { headers: Record<string, string> }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["farmer-settings"],
    queryFn: () => api.get<Settings>("/admin/farmer/settings", undefined, headers),
    retry: false,
  });
  const save = useMutation({
    mutationFn: (body: Partial<Settings>) => api.put<Settings>("/admin/farmer/settings", body, headers),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["farmer-settings"] });
      qc.invalidateQueries({ queryKey: ["lot-plan"] });
    },
  });
  if (q.isLoading) return <LoadingBlock label="Loading settings" />;
  if (q.isError) return <ErrorState error={q.error} />;
  return <SettingsForm key={JSON.stringify(q.data!.data)} s={q.data!.data} districts={(q.data!.meta.districts ?? []) as { state: string; district: string }[]} save={save} />;
}

function SettingsForm({
  s,
  districts,
  save,
}: {
  s: Settings;
  districts: { state: string; district: string }[];
  save: { mutate: (b: Partial<Settings>) => void; isPending: boolean; isError: boolean; error: unknown };
}) {
  const [loc, setLoc] = useState(s.storage_state && s.storage_district ? `${s.storage_state}|${s.storage_district}` : "");
  const [v, setV] = useState({
    transport: str(s.transport_per_q_km),
    rent: str(s.storage_rent_per_q_month),
    loss: str(s.loss_pct_per_30_days),
    fee: str(s.market_fee_pct),
    maxKm: str(s.max_km),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const [state, district] = loc.split("|");
    save.mutate({
      storage_state: state || null,
      storage_district: district || null,
      transport_per_q_km: num(v.transport),
      storage_rent_per_q_month: num(v.rent),
      loss_pct_per_30_days: num(v.loss),
      market_fee_pct: num(v.fee),
      max_km: num(v.maxKm),
    });
  };
  return (
    <Panel title="Cold storage settings">
      <form onSubmit={submit} className="space-y-4" aria-label="Cold storage settings">
        <div className="grid items-end gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <SelectField
            label="Cold storage location (district)"
            placeholder="Choose the district"
            value={loc}
            onChange={setLoc}
            options={districts.map((d) => ({ value: `${d.state}|${d.district}`, label: `${d.district}, ${d.state}` }))}
          />
          <Num label="Transport (₹ per quintal per km)" value={v.transport} onChange={(x) => setV({ ...v, transport: x })} required />
          <Num label="Storage rent (₹/quintal/month)" value={v.rent} onChange={(x) => setV({ ...v, rent: x })} required />
          <Num label="Expected loss (% per 30 days)" value={v.loss} onChange={(x) => setV({ ...v, loss: x })} required />
          <Num label="Commission + market fee (%)" value={v.fee} onChange={(x) => setV({ ...v, fee: x })} hint="Optional; 0 if blank" />
          <Num label="Only mandis within (km)" value={v.maxKm} onChange={(x) => setV({ ...v, maxKm: x })} hint="Optional" />
        </div>
        <Button type="submit" size="sm" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save settings"}
        </Button>
        {save.isError ? <ErrorState error={save.error} title="Settings not saved" /> : null}
      </form>
    </Panel>
  );
}

function LotsPanel({ headers, openLot, onOpen }: { headers: Record<string, string>; openLot: string | null; onOpen: (id: string | null) => void }) {
  const qc = useQueryClient();
  const lots = useQuery({ queryKey: ["lots"], queryFn: () => api.get<Lot[]>("/admin/lots", undefined, headers), retry: false });
  const del = useMutation({
    mutationFn: (id: string) => api.delete(`/admin/lots/${id}`, headers),
    onSuccess: (_, id) => {
      if (openLot === id) onOpen(null);
      qc.invalidateQueries({ queryKey: ["lots"] });
    },
  });
  return (
    <Panel title="Farmer lots">
      <AddLot headers={headers} onAdded={(id) => onOpen(id)} />
      <div className="mt-6">
        {lots.isLoading ? (
          <LoadingBlock />
        ) : lots.isError ? (
          <ErrorState error={lots.error} />
        ) : lots.data!.data.length === 0 ? (
          <EmptyState>No lots yet. Add the first lot above.</EmptyState>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-line" tabIndex={0} role="region" aria-label="Lots (scrolls horizontally)">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-line bg-paper-deep text-xs tracking-wider text-muted uppercase">
                <tr>
                  <th className="px-4 py-3">Farmer</th>
                  <th className="px-4 py-3">Produce</th>
                  <th className="px-4 py-3 text-right">Quantity</th>
                  <th className="px-4 py-3">Entered</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {lots.data!.data.map((l) => (
                  <tr key={l.id} className={cn("border-b border-line/60 last:border-0", openLot === l.id && "bg-sage-soft/60")}>
                    <td className="px-4 py-3">
                      <span className="font-medium">{l.farmer_name}</span>
                      <span className="block text-xs text-muted">{l.village}</span>
                    </td>
                    <td className="px-4 py-3">
                      {l.commodity}
                      <span className="block text-xs text-muted">{[l.variety, l.grade].filter(Boolean).join(" · ") || "any variety"}</span>
                    </td>
                    <td className="px-4 py-3 text-right tabular">{formatNumber(l.quantity_q, 2)} q</td>
                    <td className="px-4 py-3">{formatDate(l.entry_date)}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Button size="sm" onClick={() => onOpen(l.id)}>
                        <TrendingUp /> Sale plan
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label={`Delete lot of ${l.farmer_name}`}
                        onClick={() => window.confirm(`Delete the lot of ${l.farmer_name}?`) && del.mutate(l.id)}
                      >
                        <Trash2 />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Panel>
  );
}

function AddLot({ headers, onAdded }: { headers: Record<string, string>; onAdded: (id: string) => void }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = useState({ farmer: "", village: "", commodity: "", varietyGrade: "", qty: "", date: today });
  const commodities = useQuery({ queryKey: ["all-commodities"], queryFn: () => api.get<CommodityRow[]>("/commodities") });
  const varieties = useQuery({
    queryKey: ["all-varieties", f.commodity],
    queryFn: () => api.get<VarietyRow[]>(`/commodities/${encodeURIComponent(f.commodity)}/varieties`),
    enabled: !!f.commodity,
  });
  const add = useMutation({
    mutationFn: () => {
      const [variety, grade] = f.varietyGrade ? f.varietyGrade.split("||") : [null, null];
      return api.post<Lot>("/admin/lots", { farmer_name: f.farmer, village: f.village, commodity: f.commodity, variety, grade, quantity_q: Number(f.qty), entry_date: f.date }, headers);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["lots"] });
      setF({ farmer: "", village: "", commodity: "", varietyGrade: "", qty: "", date: today });
      onAdded(res.data.id);
    },
  });
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        add.mutate();
      }}
      className="grid items-end gap-3 rounded-xl bg-paper p-4 sm:grid-cols-2 lg:grid-cols-3"
      aria-label="Add a lot"
    >
      <Text label="Farmer name" value={f.farmer} onChange={(x) => setF({ ...f, farmer: x })} required />
      <Text label="Village" value={f.village} onChange={(x) => setF({ ...f, village: x })} required />
      <SelectField
        label="Commodity"
        placeholder={commodities.isLoading ? "Loading…" : "Choose commodity"}
        value={f.commodity}
        onChange={(x) => setF({ ...f, commodity: x, varietyGrade: "" })}
        options={(commodities.data?.data ?? []).map((c) => ({ value: c.commodity, label: c.commodity }))}
      />
      <SelectField
        label="Variety / grade (optional)"
        placeholder="Any variety"
        value={f.varietyGrade}
        onChange={(x) => setF({ ...f, varietyGrade: x })}
        disabled={!f.commodity}
        options={(varieties.data?.data ?? []).map((v) => ({ value: `${v.variety}||${v.grade}`, label: `${v.variety || "Unspecified"}${v.grade ? ` · ${v.grade}` : ""}` }))}
      />
      <Num label="Quantity (quintals)" value={f.qty} onChange={(x) => setF({ ...f, qty: x })} required />
      <Text label="Entry date" type="date" value={f.date} onChange={(x) => setF({ ...f, date: x })} required />
      <div className="sm:col-span-2 lg:col-span-3">
        <Button type="submit" size="sm" disabled={add.isPending || !f.commodity}>
          {add.isPending ? "Saving…" : "Add lot"}
        </Button>
        {add.isError ? <ErrorState error={add.error} title="Lot not saved" className="mt-3" /> : null}
      </div>
    </form>
  );
}

const WHEN = (d: number) => (d === 0 ? "Sell now" : `In ${d} days`);

function PlanPanel({ lotId, headers }: { lotId: string; headers: Record<string, string> }) {
  const q = useQuery({
    queryKey: ["lot-plan", lotId],
    queryFn: () => api.get<Plan>(`/admin/lots/${lotId}/plan`, undefined, headers),
    retry: false,
  });
  if (q.isLoading) return <LoadingBlock label="Comparing mandis and selling days" />;
  if (q.isError) return <ErrorState error={q.error} title="No sale plan" />;
  const p = q.data!.data;
  const r = p.recommendation;
  const horizons = [0, 7, 14, 30];
  return (
    <Panel title={`Sale plan: ${p.lot.farmer_name}, ${formatNumber(p.lot.quantity_q, 2)} q ${p.lot.commodity}`}>
      <div className="space-y-6" data-testid="lot-plan">
        <p className="text-sm text-muted">
          In storage {p.days_in_storage_so_far} days so far. Compared {p.mandis.length} mandis with current forecasts
          {p.skipped.no_forecast ? ` (${p.skipped.no_forecast} more trade this crop but lack enough history)` : ""}
          {p.skipped.too_far ? `, ${p.skipped.too_far} beyond your distance limit` : ""}.
        </p>
        {r ? (
          <div className="grid gap-6 rounded-card bg-forest-deep p-6 text-paper lg:grid-cols-[1.2fr_1fr]">
            <div>
              <p className="eyebrow text-amber-soft!">Best option found</p>
              <p className="mt-3 font-display text-3xl">
                {WHEN(r.sell_after_days)} at {r.market}
              </p>
              <p className="mt-1 flex items-center gap-1 text-sm text-paper/75">
                <MapPin className="size-4" aria-hidden /> {r.district}, {r.state}
                {r.km != null ? ` · ~${formatNumber(r.km, 0)} km` : " · distance unknown"} · sell on {formatDate(r.sell_on)}
              </p>
              <p className="mt-5 font-display text-5xl tabular">{formatPrice(r.net_revenue)}</p>
              <p className="text-sm text-paper/75">
                net in hand{r.net_revenue_low != null ? ` (likely ${formatPrice(r.net_revenue_low)} – ${formatPrice(r.net_revenue_high)})` : ""}
              </p>
              <p className="mt-3 text-sm">
                {r.gain_vs_best_sell_now > 0
                  ? `${formatPrice(r.gain_vs_best_sell_now)} more than the best place to sell today.`
                  : "Selling today is the best option found."}
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Cost label="Price / quintal" value={formatPrice(r.price_per_quintal)} />
              <Cost label="Quintals after loss" value={formatNumber(r.sellable_quintals, 2)} />
              <Cost label="Transport" value={formatPrice(r.transport_cost)} />
              <Cost label="Storage rent" value={formatPrice(r.storage_cost)} />
              <Cost label="Commission + fees" value={formatPrice(r.market_fee)} />
              <Cost label="Total selling cost" value={formatPrice(r.total_selling_cost)} strong />
            </dl>
          </div>
        ) : (
          <EmptyState>No mandi with a current forecast trades this commodity{p.lot.variety ? " in this variety" : ""}.</EmptyState>
        )}

        {p.mandis.length ? (
          <div className="overflow-x-auto rounded-xl border border-line" tabIndex={0} role="region" aria-label="Net money by mandi and selling day (scrolls horizontally)">
            <table className="w-full min-w-[760px] text-left text-sm">
              <caption className="sr-only">Net money in hand after transport, storage rent and fees</caption>
              <thead className="border-b border-line bg-paper-deep text-xs tracking-wider text-muted uppercase">
                <tr>
                  <th className="px-4 py-3">Mandi</th>
                  <th className="px-4 py-3 text-right">Distance</th>
                  {horizons.map((h) => (
                    <th key={h} className="px-4 py-3 text-right">
                      {WHEN(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {p.mandis.slice(0, 20).map((m) => (
                  <tr key={`${m.state}|${m.district}|${m.market}`} className="border-b border-line/60 last:border-0">
                    <td className="px-4 py-3">
                      <span className="font-medium">{m.market}</span>
                      <span className="block text-xs text-muted">
                        {m.district}, {m.state} · {[m.variety, m.grade].filter(Boolean).join(" · ")} · price of {formatDate(m.latest_price_date)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular whitespace-nowrap">
                      {m.km == null ? "—" : `${formatNumber(m.km, 0)} km`}
                      {m.km_source === "approx" ? <span className="block text-[0.7rem] text-muted">approx.</span> : null}
                    </td>
                    {horizons.map((h) => {
                      const o = m.options.find((x) => x.sell_after_days === h);
                      const isBest = o === m.best || (o && o.sell_after_days === m.best.sell_after_days);
                      return (
                        <td key={h} className={cn("px-4 py-3 text-right tabular", isBest && "bg-sage-soft font-semibold text-forest-deep")} title={o ? `Transport ${formatPrice(o.transport_cost)} · storage ${formatPrice(o.storage_cost)} · fees ${formatPrice(o.market_fee)}` : undefined}>
                          {o ? formatPrice(o.net_revenue) : "—"}
                          {o?.forecast_beats_naive_on_test === false ? <Badge tone="concept" className="ml-1">weak</Badge> : null}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
          {p.assumptions.map((a) => (
            <li key={a}>{a}</li>
          ))}
          <li>Each cell is net money in hand: sale value after loss, minus transport, storage rent (from the entry date) and fees. Highlighted = best day for that mandi.</li>
        </ul>
      </div>
    </Panel>
  );
}

function Cost({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={cn("rounded-xl bg-paper/10 p-3", strong && "bg-paper/20")}>
      <dt className="text-xs text-paper/70">{label}</dt>
      <dd className={cn("mt-1 tabular", strong ? "text-lg font-semibold" : "font-medium")}>{value}</dd>
    </div>
  );
}
