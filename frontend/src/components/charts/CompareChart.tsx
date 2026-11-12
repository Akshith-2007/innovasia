import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { axisProps, chartColors, inrTick } from "@/components/charts/theme";
import type { PriceRecord } from "@/types/api";
import { formatDate, formatPrice } from "@/lib/utils";

export function CompareChart({ rows, highlight }: { rows: PriceRecord[]; highlight?: string }) {
  const data = rows.slice(0, 15).map((r) => ({ name: r.market, modal: r.modal_price, date: r.arrival_date, district: r.district }));
  return (
    <div className="w-full" style={{ height: Math.max(220, data.length * 34 + 40) }} role="img" aria-label="Latest modal price by mandi">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
          <CartesianGrid stroke={chartColors.grid} horizontal={false} />
          <XAxis type="number" tickFormatter={inrTick} {...axisProps} />
          <YAxis type="category" dataKey="name" width={130} {...axisProps} />
          <Tooltip
            formatter={(v) => [formatPrice(v as number), "Modal"]}
            labelFormatter={(_, p) => {
              const d = p?.[0]?.payload as { name: string; date: string; district: string } | undefined;
              return d ? `${d.name}, ${d.district} · observed ${formatDate(d.date)}` : "";
            }}
            contentStyle={{ borderRadius: 12, borderColor: chartColors.grid, fontSize: 13 }}
          />
          <Bar dataKey="modal" radius={[0, 6, 6, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.name} fill={d.name === highlight ? chartColors.accent : chartColors.modal} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
