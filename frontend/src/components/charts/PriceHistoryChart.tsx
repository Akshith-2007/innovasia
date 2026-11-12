import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { axisProps, chartColors, inrTick, shortDate } from "@/components/charts/theme";
import type { PriceRecord } from "@/types/api";
import { formatDate, formatPrice } from "@/lib/utils";

/** Actual observations only: modal line + min–max band. Gaps in the data stay gaps. */
export function PriceHistoryChart({ rows }: { rows: PriceRecord[] }) {
  const data = rows.map((r) => ({
    date: r.arrival_date,
    modal: r.modal_price,
    range: r.min_price != null && r.max_price != null ? [r.min_price, r.max_price] : null,
  }));
  return (
    <div className="h-80 w-full md:h-96" role="img" aria-label={`Modal price history with minimum–maximum range, ${rows.length} observations`}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={chartColors.grid} vertical={false} />
          <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={40} {...axisProps} />
          <YAxis tickFormatter={inrTick} width={56} domain={["auto", "auto"]} {...axisProps} />
          <Tooltip
            labelFormatter={(l) => `Observed ${formatDate(String(l))}`}
            formatter={(v, name) =>
              Array.isArray(v) ? [`${formatPrice(v[0] as number)} – ${formatPrice(v[1] as number)}`, "Min–max"] : [formatPrice(v as number), name]
            }
            contentStyle={{ borderRadius: 12, borderColor: chartColors.grid, fontSize: 13 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area dataKey="range" name="Min–max range" stroke="none" fill={chartColors.band} fillOpacity={0.55} connectNulls={false} isAnimationActive={false} />
          <Line dataKey="modal" name="Modal price" stroke={chartColors.modal} strokeWidth={2} dot={rows.length < 60 ? { r: 2 } : false} connectNulls={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
