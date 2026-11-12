export const chartColors = {
  modal: "#1f4d36",
  band: "#c9d5c1",
  accent: "#c8892b",
  grid: "#e5e0d4",
  axis: "#646a63",
};

export const axisProps = {
  stroke: chartColors.axis,
  tick: { fontSize: 12, fill: chartColors.axis },
  tickLine: false,
  axisLine: false,
} as const;

export const inrTick = (v: number) =>
  v >= 1000 ? `₹${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : `₹${Math.round(v)}`;

export const shortDate = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
};
