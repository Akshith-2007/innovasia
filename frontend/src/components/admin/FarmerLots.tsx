import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, LocateFixed, Plus, Trash2, Trophy, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { EmptyState, ErrorState, LoadingBlock, SourceNote } from "@/components/layout/States";
import { Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SelectField } from "@/components/ui/field";
import { useStates } from "@/hooks/useMarketData";
import type { CommodityRow, MarketRow } from "@/types/api";
import { cn, formatDate, formatPrice } from "@/lib/utils";
import { api } from "@/services/api";

type Mandi = { market: string; district?: string | null; distance_km: number };
type Lot = {
  id: string;
  created_at: string;
  farmer_name: string;
  phone?: string | null;
  village?: string | null;
  state: string;
  latitude?: number | null;
  longitude?: number | null;
  commodity: string;
  quantity_quintals: number;
  transport_rate_per_quintal_km: number;
  mandis: Mandi[];
};
type Option = { label: string; days: number; price_per_quintal: number; transport_cost: number; storage_cost: number; market_fee: number; net_revenue: number; profit: number | null };
type MandiResult = Mandi & {
  transport_cost_per_quintal: number;
  available: boolean;
  error?: { code: string; message: string };
  latest_observation?: { date: string; modal_price: number };
  options?: Option[];
  best?: Option;
};
type Comparison = {
  mandis: MandiResult[];
  recommendation: { market: string; distance_km: number; option: Option; margin_over_next_best: number | null } | null;
  assumptions: string[];
};

const input =
  "h-10 w-full rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none";

export function FarmerLots({ password }: { password: string }) {
  const headers = { "X-Admin-Password": password };
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const lots = useQuery({ queryKey: ["admin-lots"], queryFn: () => api.get<Lot[]>("/admin/lots", undefined, headers), retry: false });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/admin/lots/${id}`, headers),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-lots"] }),
  });

  return (
    <section className="rounded-card border border-line bg-white p-6" aria-label="Farmer lots">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-medium">Farmer lots</h2>
          <p className="mt-1 text-sm text-muted">Record a lot and its nearby mandis; see which mandi and selling time pays the most after transport.</p>
        </div>
        <Button size="sm" variant={adding ? "ghost" : "primary"} onClick={() => setAdding((a) => !a)}>
          {adding ? <X /> : <Plus />} {adding ? "Cancel" : "Add lot"}
        </Button>
      </div>
      {adding ? (
        <LotForm
          headers={headers}
          onSaved={(lot) => {
            setAdding(false);
            setOpen(lot.id);
            qc.invalidateQueries({ queryKey: ["admin-lots"] });
          }}
        />
      ) : null}
      {lots.isLoading ? (
        <LoadingBlock label="Loading lots" />
      ) : lots.isError ? (
        <ErrorState error={lots.error} title="Lots unavailable" />
      ) : !lots.data!.data.length ? (
        <EmptyState>No lots yet. Add a farmer's lot to compare mandis.</EmptyState>
      ) : (
        <ul className="divide-y divide-line">
          {lots.data!.data.map((l) => (
            <li key={l.id} className="py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-charcoal">
                    {l.farmer_name} · {l.quantity_quintals} q {l.commodity}
                  </p>
                  <p className="text-xs text-muted">
                    {[l.phone, l.village, l.state].filter(Boolean).join(" · ")}
                    {l.latitude != null ? ` · ${l.latitude.toFixed(4)}, ${l.longitude?.toFixed(4)}` : ""} · {l.mandis.length} mandis · ₹
                    {l.transport_rate_per_quintal_km}/q/km · added {formatDate(l.created_at)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant={open === l.id ? "primary" : "outline"} onClick={() => setOpen(open === l.id ? null : l.id)} aria-expanded={open === l.id}>
                    {open === l.id ? "Hide" : "Best mandi"}
                  </Button>
                  <Button size="sm" variant="ghost" aria-label={`Delete lot of ${l.farmer_name}`} disabled={remove.isPending} onClick={() => confirm("Delete this lot?") && remove.mutate(l.id)}>
                    <Trash2 />
                  </Button>
                </div>
              </div>
              {open === l.id ? <CompareView id={l.id} headers={headers} /> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CompareView({ id, headers }: { id: string; headers: Record<string, string> }) {
  const q = useQuery({ queryKey: ["admin-lot-compare", id], queryFn: () => api.get<Comparison>(`/admin/lots/${id}/compare`, undefined, headers), retry: false });
  if (q.isLoading) return <LoadingBlock label="Forecasting each mandi" className="mt-4" />;
  if (q.isError) return <ErrorState error={q.error} title="Comparison failed" className="mt-4" />;
  const c = q.data!.data;
  const rec = c.recommendation;
  return (
    <div className="mt-4 space-y-4">
      {rec ? (
        <div className={cn("flex items-start gap-3 rounded-xl p-4", losing(rec.option) ? "bg-danger/10" : "bg-sage/40")}>
          {losing(rec.option) ? (
            <AlertTriangle className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
          ) : (
            <Trophy className="mt-0.5 size-5 shrink-0 text-forest" aria-hidden />
          )}
          <p className="text-sm">
            {losing(rec.option) ? "Every option loses money. Smallest loss: " : ""}
            <strong>{rec.market}</strong> ({rec.distance_km} km): <strong>{rec.option.label.toLowerCase()}</strong>
            {rec.option.net_revenue < 0 ? (
              <>
                {" "}
                — transport, fees and storage cost <strong className="text-danger">{formatPrice(-rec.option.net_revenue)} more</strong> than the sale brings in
              </>
            ) : (
              <>
                {" "}
                for about <strong>{formatPrice(rec.option.net_revenue)}</strong> after transport, fees and storage
              </>
            )}
            {rec.option.profit != null ? (
              <>
                {" "}
                (<Money value={rec.option.profit} gain="profit" /> after production cost)
              </>
            ) : null}
            {rec.margin_over_next_best != null ? `, ${formatPrice(rec.margin_over_next_best)} better than the next-best mandi.` : "."}
          </p>
        </div>
      ) : (
        <EmptyState>No mandi in this lot has a supported price series and forecast, so no recommendation is made.</EmptyState>
      )}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-xs text-muted">
            <tr>
              <th className="py-2 pr-3 font-semibold">Mandi</th>
              <th className="py-2 pr-3 font-semibold">Option</th>
              <th className="py-2 pr-3 text-right font-semibold">Price ₹/q</th>
              <th className="py-2 pr-3 text-right font-semibold">Transport</th>
              <th className="py-2 pr-3 text-right font-semibold">Fees + storage</th>
              <th className="py-2 text-right font-semibold">Net receipts / loss</th>
            </tr>
          </thead>
          <tbody>
            {c.mandis.map((m) =>
              m.available ? (
                m.options!.map((o, i) => {
                  const top = rec?.market === m.market && rec.option.days === o.days;
                  return (
                    <tr key={`${m.market}-${o.days}`} className={cn("border-t border-line", top && "bg-sage/30 font-semibold")}>
                      <td className="py-2 pr-3">{i === 0 ? `${m.market} (${m.distance_km} km)` : ""}</td>
                      <td className="py-2 pr-3">{o.label}</td>
                      <td className="py-2 pr-3 text-right tabular">{formatPrice(o.price_per_quintal)}</td>
                      <td className="py-2 pr-3 text-right tabular">{formatPrice(o.transport_cost)}</td>
                      <td className="py-2 pr-3 text-right tabular">{formatPrice(o.market_fee + o.storage_cost)}</td>
                      <td className="py-2 text-right tabular">
                        <Money value={o.net_revenue} />
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr key={m.market} className="border-t border-line">
                  <td className="py-2 pr-3">
                    {m.market} ({m.distance_km} km)
                  </td>
                  <td colSpan={5} className="py-2 text-muted">
                    <Badge tone="warn">No figure</Badge> {m.error?.message}
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
      <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
        {c.assumptions.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
      <SourceNote source={q.data!.source} />
    </div>
  );
}

// A lot loses money when sale receipts don't cover costs (or production cost, when it was entered).
const losing = (o: Option) => (o.profit ?? o.net_revenue) < 0;

// Negative amounts read as "Loss ₹X", never "₹-X". `gain` labels positive amounts (e.g. "Profit").
function Money({ value, gain }: { value: number; gain?: string }) {
  if (value < 0) return <span className="font-semibold text-danger">Loss {formatPrice(-value)}</span>;
  return <span>{gain && value > 0 ? `${gain} ${formatPrice(value)}` : formatPrice(value)}</span>;
}

function LotForm({ headers, onSaved }: { headers: Record<string, string>; onSaved: (l: Lot) => void }) {
  const states = useStates();
  const [f, setF] = useState({ farmer_name: "", phone: "", village: "", state: "", latitude: "", longitude: "", commodity: "", quantity: "", total_cost: "", rate: "", fee: "", storage: "sell_now", storage_cost: "", loss: "" });
  const [mandis, setMandis] = useState<{ market: string; district: string; km: string }[]>([]);
  const [geoMsg, setGeoMsg] = useState("");
  const set = (k: keyof typeof f) => (v: string) => setF((o) => ({ ...o, [k]: v }));
  const commodities = useQuery({
    queryKey: ["lot-commodities", f.state],
    queryFn: () => api.get<CommodityRow[]>("/commodities", { state: f.state }),
    enabled: !!f.state,
  });
  const markets = useQuery({
    queryKey: ["lot-markets", f.state, f.commodity],
    queryFn: () => api.get<MarketRow[]>("/markets/list", { state: f.state, commodity: f.commodity }),
    enabled: !!f.state && !!f.commodity,
  });
  const storageOpts = useQuery({
    queryKey: ["lot-storage", f.commodity],
    queryFn: () => api.get<{ options: { id: string; name: string; suited: boolean; default_cost_per_quintal_per_month: number | null; default_loss_pct_per_30_days: number | null }[] }>("/decision/storage-options", { commodity: f.commodity }),
    enabled: !!f.commodity,
  });
  const opt = storageOpts.data?.data.options.find((o) => o.id === f.storage);
  const save = useMutation({
    mutationFn: (body: unknown) => api.post<Lot>("/admin/lots", body, headers),
    onSuccess: (r) => onSaved(r.data),
  });
  const num = (v: string) => (v === "" ? null : Number(v));
  const locate = () => {
    if (!navigator.geolocation) return setGeoMsg("This browser cannot share location; type it in.");
    setGeoMsg("Locating…");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setF((o) => ({ ...o, latitude: p.coords.latitude.toFixed(5), longitude: p.coords.longitude.toFixed(5) }));
        setGeoMsg(`Accurate to about ${Math.round(p.coords.accuracy)} m.`);
      },
      (e) => setGeoMsg(`Location unavailable: ${e.message}`),
    );
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate({
      farmer_name: f.farmer_name,
      phone: f.phone.trim(),
      village: f.village || null,
      state: f.state,
      latitude: num(f.latitude),
      longitude: num(f.longitude),
      commodity: f.commodity,
      quantity_quintals: Number(f.quantity),
      total_cost: num(f.total_cost),
      transport_rate_per_quintal_km: Number(f.rate),
      market_fee_pct: num(f.fee),
      storage_option: f.storage,
      storage_cost_per_quintal_per_month: num(f.storage_cost),
      loss_pct_per_30_days: num(f.loss),
      mandis: mandis.map((m) => ({ market: m.market, district: m.district || null, distance_km: Number(m.km) })),
    });
  };
  const chosen = new Set(mandis.map((m) => m.market));
  const ready = f.farmer_name && f.phone.trim() && f.state && f.commodity && f.quantity && f.rate !== "" && mandis.length && mandis.every((m) => m.km !== "");

  return (
    <form onSubmit={submit} className="mb-6 space-y-5 rounded-xl bg-paper p-5">
      <fieldset className="grid gap-3 sm:grid-cols-3">
        <legend className="mb-2 text-sm font-semibold text-charcoal">Farmer and location</legend>
        <Text label="Farmer name" value={f.farmer_name} onChange={set("farmer_name")} required />
        <Text label="Phone" value={f.phone} onChange={set("phone")} type="tel" required />
        <Text label="Village" value={f.village} onChange={set("village")} />
        <Text label="Latitude" value={f.latitude} onChange={set("latitude")} type="number" />
        <Text label="Longitude" value={f.longitude} onChange={set("longitude")} type="number" />
        <div className="flex flex-col justify-end gap-1">
          <Button type="button" size="sm" variant="outline" className="text-forest" onClick={locate}>
            <LocateFixed /> Use this device's location
          </Button>
          {geoMsg ? <p className="text-xs text-muted" role="status">{geoMsg}</p> : null}
        </div>
      </fieldset>

      <fieldset className="grid gap-3 sm:grid-cols-3">
        <legend className="mb-2 text-sm font-semibold text-charcoal">Produce and costs</legend>
        <SelectField
          label="State"
          value={f.state}
          onChange={(v) => {
            setF((o) => ({ ...o, state: v, commodity: "", storage: "sell_now" }));
            setMandis([]);
          }}
          options={(states.data?.data ?? []).map((s) => ({ value: s, label: s }))}
          placeholder={states.isError ? "No market data loaded" : "Choose state"}
        />
        <SelectField
          label="Commodity"
          value={f.commodity}
          onChange={(v) => {
            setF((o) => ({ ...o, commodity: v, storage: "sell_now" }));
            setMandis([]);
          }}
          options={(commodities.data?.data ?? []).map((c) => ({ value: c.commodity, label: c.commodity }))}
          placeholder="Choose commodity"
          disabled={!f.state}
        />
        <Text label="Quantity (quintals)" value={f.quantity} onChange={set("quantity")} type="number" required />
        <Text label="Total production cost ₹ (optional)" value={f.total_cost} onChange={set("total_cost")} type="number" />
        <Text label="Transport fare ₹ per quintal per km" value={f.rate} onChange={set("rate")} type="number" required />
        <Text label="Commission + market fee % (optional)" value={f.fee} onChange={set("fee")} type="number" />
        <SelectField
          label="Storage before selling"
          value={f.storage}
          onChange={(v) => setF((o) => ({ ...o, storage: v || "sell_now", storage_cost: "", loss: "" }))}
          options={(storageOpts.data?.data.options ?? []).filter((o) => o.suited).map((o) => ({ value: o.id, label: o.name }))}
          placeholder="Sell now only"
          disabled={!f.commodity}
          hint="Choose a storage option to also compare 7, 14 and 30-day forecasts."
        />
        {f.storage !== "sell_now" ? (
          <>
            <Text
              label={`Storage ₹/q/month${opt?.default_cost_per_quintal_per_month != null ? ` (cited default ${opt.default_cost_per_quintal_per_month})` : " (required)"}`}
              value={f.storage_cost}
              onChange={set("storage_cost")}
              type="number"
              required={opt?.default_cost_per_quintal_per_month == null}
            />
            <Text
              label={`Loss % per 30 days${opt?.default_loss_pct_per_30_days != null ? ` (cited default ${opt.default_loss_pct_per_30_days})` : " (required)"}`}
              value={f.loss}
              onChange={set("loss")}
              type="number"
              required={opt?.default_loss_pct_per_30_days == null}
            />
          </>
        ) : null}
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="mb-2 text-sm font-semibold text-charcoal">Nearby mandis and road distance</legend>
        <SelectField
          label="Add a mandi that trades this commodity"
          value=""
          onChange={(v) => {
            const m = markets.data?.data.find((x) => x.market === v);
            if (m) setMandis((o) => [...o, { market: m.market, district: m.district, km: "" }]);
          }}
          options={(markets.data?.data ?? []).filter((m) => !chosen.has(m.market)).map((m) => ({ value: m.market, label: `${m.market} — ${m.district}` }))}
          placeholder={f.commodity ? "Choose mandi" : "Choose state and commodity first"}
          disabled={!f.commodity}
          hint="Enter road distance from the lot (e.g. from Google Maps directions). Distances are not guessed."
        />
        {mandis.map((m, i) => (
          <div key={m.market} className="flex items-end gap-3">
            <p className="min-w-0 flex-1 truncate pb-2 text-sm">
              {m.market} <span className="text-muted">— {m.district}</span>
            </p>
            <div className="w-36">
              <Text label="Distance (km)" value={m.km} onChange={(v) => setMandis((o) => o.map((x, j) => (j === i ? { ...x, km: v } : x)))} type="number" required />
            </div>
            <Button type="button" size="sm" variant="ghost" aria-label={`Remove ${m.market}`} onClick={() => setMandis((o) => o.filter((_, j) => j !== i))}>
              <X />
            </Button>
          </div>
        ))}
      </fieldset>

      <Button type="submit" disabled={!ready || save.isPending}>
        {save.isPending ? "Saving…" : "Save lot and compare"}
      </Button>
      {save.isError ? <ErrorState error={save.error} title="Lot not saved" /> : null}
    </form>
  );
}

function Text({ label, value, onChange, type = "text", required }: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) {
  const id = `lot-${label.replace(/\W+/g, "-")}`;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      <input id={id} type={type} step="any" className={input} value={value} onChange={(e) => onChange(e.target.value)} required={required} />
    </div>
  );
}
