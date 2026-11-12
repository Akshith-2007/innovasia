import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Droplets, Info, LogOut, Power, Thermometer, Waves } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { FarmerLots } from "@/components/admin/FarmerLots";
import { axisProps, chartColors } from "@/components/charts/theme";
import { ErrorState, LoadingBlock } from "@/components/layout/States";
import { Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, formatNumber } from "@/lib/utils";
import { api, ApiError } from "@/services/api";

type Reading = { chamber_temp_c: number | null; humidity_pct: number | null; coil_temp_c: number | null; pump_on: boolean };
type DeviceStatus = {
  mode: "manual" | "auto";
  pump_on: boolean;
  auto: { upper_c: number | null; lower_c: number | null };
  pcm: Record<PcmKey, number | null> & { state_of_charge: number };
  pcm_estimate?:
    | { configured: false; missing: string[] }
    | {
        configured: true;
        capacity_kj: number;
        remaining_kj: number;
        state_of_charge: number;
        ua_w_per_k: number;
        heat_load_w: number;
        charge_w: number | null;
        remaining_hours: number | null;
        full_backup_hours: number | null;
      };
  online: boolean;
  seconds_since_seen: number | null;
  last_reading: (Reading & { received_at: string }) | null;
  recommendations: { level: "ok" | "info" | "warn"; text: string }[];
  pcm_note: string;
};
type PcmKey = "mass_kg" | "latent_kj_per_kg" | "melt_c" | "ambient_c" | "wall_area_m2" | "insulation_mm" | "insulation_k" | "coil_w_per_k";
type Row = {
  received_at: string;
  chamber_temp_c: number | null;
  humidity_pct: number | null;
  coil_temp_c: number | null;
  pump_on_reported: boolean;
  pcm_remaining_h: number | null;
  pcm_soc: number | null;
  heat_load_w: number | null;
};

const KEY = "kcl-admin-password";
const readSaved = () => {
  try {
    return sessionStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
};

export default function AdminPage() {
  const [password, setPassword] = useState(readSaved);
  const save = (p: string) => {
    try {
      if (p) sessionStorage.setItem(KEY, p);
      else sessionStorage.removeItem(KEY);
    } catch {
      /* private mode: keep in memory only */
    }
    setPassword(p);
  };
  return (
    <section className="container-site pt-28 pb-20 md:pt-32">
      <title>Cold Storage Admin — Kisan Cold Link</title>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Cold storage admin</p>
          <h1 className="mt-3 text-4xl font-medium md:text-5xl">Chamber monitor</h1>
          <p className="mt-2 text-muted">Live readings from the ESP32 node, pump control and a physics-based PCM backup estimate.</p>
        </div>
        {password ? (
          <Button variant="ghost" size="sm" onClick={() => save("")}>
            <LogOut /> Sign out
          </Button>
        ) : null}
      </div>
      <div className="mt-10">{password ? <Tabs password={password} onAuthFail={() => save("")} /> : <Login onLogin={save} />}</div>
    </section>
  );
}

function Tabs({ password, onAuthFail }: { password: string; onAuthFail: () => void }) {
  const [tab, setTab] = useState<"chamber" | "lots">("chamber");
  const tabs = [
    { id: "chamber", label: "Chamber monitor" },
    { id: "lots", label: "Farmer lots & best mandi" },
  ] as const;
  return (
    <div className="space-y-8">
      <div role="tablist" aria-label="Admin sections" className="flex flex-wrap gap-2 border-b border-line pb-3">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "rounded-full px-4 py-2 text-sm font-semibold transition-colors",
              tab === t.id ? "bg-forest text-paper" : "text-forest hover:bg-sage-soft",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "chamber" ? <Dashboard password={password} onAuthFail={onAuthFail} /> : <FarmerLots password={password} />}
      </div>
    </div>
  );
}

function Login({ onLogin }: { onLogin: (p: string) => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.get("/admin/device", undefined, { "X-Admin-Password": value });
      onLogin(value);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="max-w-sm space-y-4 rounded-card border border-line bg-white p-6">
      <label htmlFor="admin-pw" className="block text-sm font-semibold text-charcoal">
        Admin password
      </label>
      <input
        id="admin-pw"
        type="password"
        autoComplete="current-password"
        className="h-11 w-full rounded-xl border border-line px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        required
      />
      <Button type="submit" disabled={busy || !value} className="w-full">
        {busy ? "Checking…" : "Sign in"}
      </Button>
      {error ? <ErrorState error={error} title="Sign-in failed" /> : null}
    </form>
  );
}

function Dashboard({ password, onAuthFail }: { password: string; onAuthFail: () => void }) {
  const headers = { "X-Admin-Password": password };
  const qc = useQueryClient();
  const [hours, setHours] = useState(6);
  const status = useQuery({
    queryKey: ["admin-device"],
    queryFn: () => api.get<DeviceStatus>("/admin/device", undefined, headers),
    refetchInterval: 5000,
    retry: false,
  });
  const telemetry = useQuery({
    queryKey: ["admin-telemetry", hours],
    queryFn: () => api.get<Row[]>("/admin/telemetry", { hours }, headers),
    refetchInterval: 15000,
    retry: false,
  });
  const control = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put<DeviceStatus>("/admin/device/control", body, headers),
    onSuccess: (res) => qc.setQueryData(["admin-device"], res),
  });

  const unauthorized = status.error instanceof ApiError && status.error.code === "unauthorized";
  useEffect(() => {
    if (unauthorized) onAuthFail(); // password changed on the server: back to sign-in
  }, [unauthorized, onAuthFail]);
  if (unauthorized) return null;
  if (status.isLoading) return <LoadingBlock label="Connecting to the chamber" />;
  if (status.isError) return <ErrorState error={status.error} title="Admin data unavailable" />;
  const s = status.data!.data;
  const r = s.last_reading;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-3 text-sm" role="status" aria-live="polite">
        {s.online ? <Badge tone="live">Device online</Badge> : <Badge tone="warn">Device offline</Badge>}
        <span className="text-muted">
          {s.seconds_since_seen == null ? "No readings received yet." : `Last reading ${Math.round(s.seconds_since_seen)} s ago.`}
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile icon={Thermometer} label="Chamber air (DHT11)" value={fmt(r?.chamber_temp_c, "°C")} />
        <Tile icon={Droplets} label="Humidity (DHT11)" value={fmt(r?.humidity_pct, "%", 0)} />
        <Tile icon={Waves} label="Coil / heat sink (DS18B20)" value={fmt(r?.coil_temp_c, "°C")} />
        <Tile
          icon={Power}
          label="Pump"
          value={r ? (r.pump_on ? "ON" : "OFF") : "—"}
          sub={`Command: ${s.pump_on ? "ON" : "OFF"} · ${s.mode === "auto" ? "Auto" : "Manual"}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel title="Pump control">
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => control.mutate({ pump_on: true })} disabled={control.isPending} variant={s.pump_on ? "primary" : "outline"} className={s.pump_on ? "" : "text-forest"}>
              Pump ON
            </Button>
            <Button onClick={() => control.mutate({ pump_on: false })} disabled={control.isPending} variant={!s.pump_on ? "primary" : "outline"} className={!s.pump_on ? "" : "text-forest"}>
              Pump OFF
            </Button>
          </div>
          <p className="mt-2 text-xs text-muted">A manual press switches the chamber to Manual mode. The ESP32 applies it within about 5 seconds.</p>
          <AutoForm key={`${s.auto.upper_c}-${s.auto.lower_c}-${s.mode}`} status={s} onSave={(b) => control.mutate(b)} busy={control.isPending} />
          {control.isError ? <ErrorState error={control.error} title="Change not saved" className="mt-4" /> : null}
        </Panel>

        <Panel title="PCM backup (physics estimate)">
          <PcmEstimate status={s} />
          <PcmForm key={JSON.stringify(s.pcm)} status={s} onSave={(b) => control.mutate(b)} busy={control.isPending} />
        </Panel>
      </div>

      <Panel title="Efficient use">
        <ul className="space-y-2">
          {s.recommendations.map((t) => (
            <li key={t.text} className="flex items-start gap-3 text-sm">
              {t.level === "warn" ? <AlertTriangle className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden /> : t.level === "ok" ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-forest" aria-hidden /> : <Info className="mt-0.5 size-4 shrink-0 text-amber-ink" aria-hidden />}
              <span>{t.text}</span>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel
        title="Telemetry"
        action={
          <div className="flex gap-1" role="group" aria-label="Time range">
            {[1, 6, 24].map((h) => (
              <Button key={h} size="sm" variant={hours === h ? "primary" : "ghost"} onClick={() => setHours(h)} aria-pressed={hours === h}>
                {h} h
              </Button>
            ))}
          </div>
        }
      >
        {telemetry.isLoading ? <LoadingBlock /> : telemetry.isError ? <ErrorState error={telemetry.error} /> : <Charts rows={telemetry.data!.data} />}
      </Panel>
    </div>
  );
}

function AutoForm({ status, onSave, busy }: { status: DeviceStatus; onSave: (b: Record<string, unknown>) => void; busy: boolean }) {
  const [upper, setUpper] = useState(status.auto.upper_c?.toString() ?? "");
  const [lower, setLower] = useState(status.auto.lower_c?.toString() ?? "");
  const limits = { upper_c: upper === "" ? null : Number(upper), lower_c: lower === "" ? null : Number(lower) };
  return (
    <div className="mt-6 border-t border-line pt-5">
      <p className="text-sm font-semibold text-charcoal">Automatic thermostat</p>
      <p className="mt-1 text-xs text-muted">Pump turns ON above the upper limit and OFF below the lower limit (chamber air temperature).</p>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <NumberField label="Upper limit °C" value={upper} onChange={setUpper} />
        <NumberField label="Lower limit °C" value={lower} onChange={setLower} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" disabled={busy} onClick={() => onSave({ auto: limits, mode: "auto" })}>
          {status.mode === "auto" ? "Update limits" : "Save & switch to Auto"}
        </Button>
        {status.mode === "auto" ? (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onSave({ mode: "manual" })}>
            Back to Manual
          </Button>
        ) : null}
      </div>
    </div>
  );
}

const PCM_PRESETS: Record<string, { label: string; latent: number; melt: number } | null> = {
  water: { label: "Water / ice (334 kJ/kg, melts at 0 °C)", latent: 334, melt: 0 },
  custom: null,
};
// Typical conductivities (W/m·K); real values vary by density and age, so the datasheet value wins.
const INSULATION: Record<string, { label: string; k: number } | null> = {
  puf: { label: "PUF panel (typical ≈ 0.023 W/m·K)", k: 0.023 },
  xps: { label: "XPS board (typical ≈ 0.032 W/m·K)", k: 0.032 },
  eps: { label: "EPS / thermocol (typical ≈ 0.036 W/m·K)", k: 0.036 },
  custom: null,
};

function PcmEstimate({ status }: { status: DeviceStatus }) {
  const e = status.pcm_estimate;
  if (!e?.configured)
    return (
      <p className="rounded-xl bg-paper p-4 text-sm text-muted">
        Enter the PCM and chamber details below. Backup time is then calculated from the stored latent heat and the heat leaking in, not assumed.
      </p>
    );
  const pct = Math.round(e.state_of_charge * 100);
  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-display text-4xl tabular text-forest">{e.remaining_hours == null ? "—" : `${formatNumber(e.remaining_hours, 1)} h`}</span>
        <span className="text-sm text-muted">
          {e.remaining_hours == null ? "no heat is leaking in at the current temperatures" : "left at the current heat load"}
        </span>
      </div>
      <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-paper-deep" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Estimated PCM charge">
        <div className={cn("h-full rounded-full", pct < 20 ? "bg-danger" : pct < 50 ? "bg-amber" : "bg-forest")} style={{ width: `${pct}%` }} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <Stat label="PCM charged" value={`${pct}%`} />
        <Stat label="Heat leaking in" value={`${formatNumber(e.heat_load_w, 0)} W`} />
        <Stat label="Recharge power" value={e.charge_w == null ? "not modelled" : `${formatNumber(e.charge_w, 0)} W`} />
        <Stat label="Stored cold" value={`${formatNumber(e.remaining_kj, 0)} / ${formatNumber(e.capacity_kj, 0)} kJ`} />
        <Stat label="Insulation UA" value={`${formatNumber(e.ua_w_per_k, 2)} W/K`} />
        <Stat label="Full charge lasts" value={e.full_backup_hours == null ? "—" : `${formatNumber(e.full_backup_hours, 1)} h`} />
      </dl>
      <p className="mt-3 text-xs text-muted">
        Stored = mass × latent heat. Heat in = area × k ÷ thickness × (outside − chamber). Backup = stored ÷ heat in. {status.pcm_note}
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-semibold tabular text-charcoal">{value}</dd>
    </div>
  );
}

function PcmForm({ status, onSave, busy }: { status: DeviceStatus; onSave: (b: Record<string, unknown>) => void; busy: boolean }) {
  const init = (k: PcmKey) => (status.pcm[k] == null ? "" : String(status.pcm[k]));
  const [v, setV] = useState<Record<PcmKey, string>>({
    mass_kg: init("mass_kg"),
    latent_kj_per_kg: init("latent_kj_per_kg"),
    melt_c: init("melt_c"),
    ambient_c: init("ambient_c"),
    wall_area_m2: init("wall_area_m2"),
    insulation_mm: init("insulation_mm"),
    insulation_k: init("insulation_k"),
    coil_w_per_k: init("coil_w_per_k"),
  });
  const set = (k: PcmKey) => (x: string) => setV((o) => ({ ...o, [k]: x }));
  const pcm = Object.fromEntries(Object.entries(v).filter(([, x]) => x !== "").map(([k, x]) => [k, Number(x)]));
  return (
    <div className="mt-5 space-y-3 border-t border-line pt-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <PresetSelect
          label="PCM type"
          options={PCM_PRESETS}
          onPick={(p) => p && setV((o) => ({ ...o, latent_kj_per_kg: String(p.latent), melt_c: String(p.melt) }))}
        />
        <PresetSelect label="Insulation" options={INSULATION} onPick={(p) => p && setV((o) => ({ ...o, insulation_k: String(p.k) }))} />
      </div>
      <div className="grid grid-cols-2 items-end gap-3 sm:grid-cols-4">
        <NumberField label="PCM mass (kg)" value={v.mass_kg} onChange={set("mass_kg")} />
        <NumberField label="Latent heat (kJ/kg)" value={v.latent_kj_per_kg} onChange={set("latent_kj_per_kg")} />
        <NumberField label="Melting point °C" value={v.melt_c} onChange={set("melt_c")} />
        <NumberField label="Outside temp °C" value={v.ambient_c} onChange={set("ambient_c")} />
        <NumberField label="Insulated area (m²)" value={v.wall_area_m2} onChange={set("wall_area_m2")} />
        <NumberField label="Insulation (mm)" value={v.insulation_mm} onChange={set("insulation_mm")} />
        <NumberField label="Conductivity k (W/m·K)" value={v.insulation_k} onChange={set("insulation_k")} />
        <NumberField label="Coil transfer (W/K, optional)" value={v.coil_w_per_k} onChange={set("coil_w_per_k")} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={busy} onClick={() => onSave({ pcm })}>
          Save PCM settings
        </Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => onSave({ pcm_reset_full: true })}>
          Mark fully charged
        </Button>
      </div>
      <p className="text-xs text-muted">
        Insulated area = all walls + top + bottom. Without a coil transfer value the PCM is not modelled as recharging; use “Mark fully charged” after a full
        cooling run.
      </p>
    </div>
  );
}

function PresetSelect<T>({ label, options, onPick }: { label: string; options: Record<string, (T & { label: string }) | null>; onPick: (p: T | null) => void }) {
  const id = `ps-${label.replace(/\W+/g, "-")}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      <select
        id={id}
        defaultValue=""
        onChange={(e) => onPick(options[e.target.value] ?? null)}
        className="h-10 rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none"
      >
        <option value="">Choose a preset (optional)</option>
        {Object.entries(options).map(([k, o]) => (
          <option key={k} value={k}>
            {o ? o.label : "Custom (enter below)"}
          </option>
        ))}
      </select>
    </div>
  );
}

function Charts({ rows }: { rows: Row[] }) {
  if (!rows.length) return <p className="py-10 text-center text-sm text-muted">No telemetry in this period yet.</p>;
  const data = rows.map((r) => ({
    ...r,
    t: new Date(r.received_at).getTime(),
    pump: r.pump_on_reported ? 1 : 0,
    soc_pct: r.pcm_soc == null ? null : Math.round(r.pcm_soc * 1000) / 10,
  }));
  const time = (v: number) => new Date(v).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  const tip = { labelFormatter: (v: unknown) => new Date(Number(v)).toLocaleString("en-IN"), contentStyle: { borderRadius: 12, fontSize: 13 } };
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <ChartBox label="Temperatures (°C)">
        <LineChart data={data}>
          <CartesianGrid stroke={chartColors.grid} vertical={false} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={time} {...axisProps} />
          <YAxis width={40} {...axisProps} />
          <Tooltip {...tip} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line dataKey="chamber_temp_c" name="Chamber air" stroke={chartColors.modal} dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
          <Line dataKey="coil_temp_c" name="Coil / heat sink" stroke="#3a7ca5" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
        </LineChart>
      </ChartBox>
      <ChartBox label="Humidity (%)">
        <LineChart data={data}>
          <CartesianGrid stroke={chartColors.grid} vertical={false} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={time} {...axisProps} />
          <YAxis width={40} domain={[0, 100]} {...axisProps} />
          <Tooltip {...tip} />
          <Line dataKey="humidity_pct" name="Humidity" stroke={chartColors.accent} dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
        </LineChart>
      </ChartBox>
      <ChartBox label="Pump (1 = ON)">
        <LineChart data={data}>
          <CartesianGrid stroke={chartColors.grid} vertical={false} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={time} {...axisProps} />
          <YAxis width={40} domain={[0, 1]} ticks={[0, 1]} {...axisProps} />
          <Tooltip {...tip} />
          <Line type="stepAfter" dataKey="pump" name="Pump" stroke={chartColors.modal} dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ChartBox>
      <ChartBox label="PCM charge (%) and heat leaking in (W)">
        <LineChart data={data}>
          <CartesianGrid stroke={chartColors.grid} vertical={false} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={time} {...axisProps} />
          <YAxis width={40} {...axisProps} />
          <Tooltip {...tip} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line dataKey="soc_pct" name="PCM charge %" stroke={chartColors.accent} dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line dataKey="heat_load_w" name="Heat in (W)" stroke="#3a7ca5" dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ChartBox>
    </div>
  );
}

function ChartBox({ label, children }: { label: string; children: React.ReactElement }) {
  return (
    <figure>
      <figcaption className="mb-2 text-sm font-semibold text-charcoal">{label}</figcaption>
      <div className="h-56" role="img" aria-label={`${label} over time`}>
        <ResponsiveContainer>{children}</ResponsiveContainer>
      </div>
    </figure>
  );
}

function Tile({ icon: Icon, label, value, sub }: { icon: typeof Thermometer; label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-card border border-line bg-white p-5">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted">
        <Icon className="size-4 text-forest" aria-hidden /> {label}
      </div>
      <p className="mt-3 font-display text-3xl tabular text-charcoal">{value}</p>
      {sub ? <p className="mt-1 text-xs text-muted">{sub}</p> : null}
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

function NumberField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const id = `nf-${label.replace(/\W+/g, "-")}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted">
        {label}
      </label>
      <input id={id} type="number" step="0.1" inputMode="decimal" className="h-10 rounded-xl border border-line bg-white px-3 text-sm focus:border-forest focus:ring-2 focus:ring-forest/20 focus:outline-none" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function fmt(v: number | null | undefined, unit: string, digits = 1) {
  return v == null ? "—" : `${formatNumber(v, digits)}${unit === "%" ? "%" : ` ${unit}`}`;
}
