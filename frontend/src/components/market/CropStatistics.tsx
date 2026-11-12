import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { axisProps, chartColors } from "@/components/charts/theme";
import { EmptyState, ErrorState, LoadingBlock, SourceNote } from "@/components/layout/States";
import { SelectField } from "@/components/ui/field";
import { useAgriOptions, useDistrictComparison, useProduction } from "@/hooks/useMarketData";
import { formatNumber } from "@/lib/utils";

const compact = (v: number) => new Intl.NumberFormat("en-IN", { notation: "compact" }).format(v);

export function CropStatistics() {
  const options = useAgriOptions();
  const [state, setState] = useState("");
  const [crop, setCrop] = useState("");
  const prod = useProduction(state, crop);
  const dist = useDistrictComparison(state, crop);

  if (options.isLoading) return <LoadingBlock label="Loading crop statistics" />;
  if (options.isError) return <ErrorState error={options.error} title="Crop statistics unavailable" />;
  const o = options.data!.data;

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 lg:max-w-2xl">
        <SelectField label="State" placeholder="Select a state" value={state} options={o.states.map((s) => ({ value: s, label: s }))} onChange={setState} />
        <SelectField label="Crop" placeholder="Select a crop" value={crop} options={o.crops.map((s) => ({ value: s, label: s }))} onChange={setCrop} />
      </div>
      {!state || !crop ? (
        <EmptyState>Select a state and crop to see district production statistics.</EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-card border border-line bg-white p-5">
            <h3 className="text-lg font-medium">Production over time</h3>
            {prod.isLoading ? <LoadingBlock /> : prod.isError ? <ErrorState error={prod.error} /> : (
              <>
                <p className="mt-1 text-xs text-muted">Unit: {prod.data!.data[0]?.production_unit ?? "—"} · state total across reporting districts</p>
                <div className="mt-4 h-64" role="img" aria-label="Production by year">
                  <ResponsiveContainer>
                    <LineChart data={prod.data!.data}>
                      <CartesianGrid stroke={chartColors.grid} vertical={false} />
                      <XAxis dataKey="year" {...axisProps} />
                      <YAxis tickFormatter={compact} width={52} {...axisProps} />
                      <Tooltip formatter={(v) => formatNumber(v as number)} contentStyle={{ borderRadius: 12, fontSize: 13 }} />
                      <Line dataKey="production" name="Production" stroke={chartColors.modal} strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <SourceNote source={prod.data!.source} className="mt-3" />
              </>
            )}
          </div>
          <div className="rounded-card border border-line bg-white p-5">
            <h3 className="text-lg font-medium">
              District comparison{dist.data ? ` · ${String(dist.data.meta.year)}` : ""}
            </h3>
            {dist.isLoading ? <LoadingBlock /> : dist.isError ? <ErrorState error={dist.error} /> : (
              <>
                <p className="mt-1 text-xs text-muted">{String(dist.data!.meta.note ?? "")}</p>
                <div className="mt-4" style={{ height: Math.max(220, Math.min(dist.data!.data.length, 12) * 28 + 40) }} role="img" aria-label="Production by district">
                  <ResponsiveContainer>
                    <BarChart data={dist.data!.data.slice(0, 12)} layout="vertical">
                      <CartesianGrid stroke={chartColors.grid} horizontal={false} />
                      <XAxis type="number" tickFormatter={compact} {...axisProps} />
                      <YAxis type="category" dataKey="district" width={110} {...axisProps} />
                      <Tooltip formatter={(v) => formatNumber(v as number)} contentStyle={{ borderRadius: 12, fontSize: 13 }} />
                      <Bar dataKey="production" name="Production" fill={chartColors.modal} radius={[0, 6, 6, 0]} isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
