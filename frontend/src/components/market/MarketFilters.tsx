import { useEffect, useRef } from "react";

import { ErrorState, LoadingBlock } from "@/components/layout/States";
import { DateField, SelectField } from "@/components/ui/field";
import { formatDate } from "@/lib/utils";
import {
  type Selection,
  useCommodities,
  useDistricts,
  useMarkets,
  useStates,
  useVarieties,
} from "@/hooks/useMarketData";

const opts = (xs: string[]) => xs.map((x) => ({ value: x, label: x }));

export function MarketFilters({ value, onChange }: { value: Selection; onChange: (s: Selection) => void }) {
  const states = useStates();
  const districts = useDistricts(value.state);
  const markets = useMarkets(value.state, value.district);
  const commodities = useCommodities(value.state, value.district, value.market);
  const varieties = useVarieties(value.commodity, value.market);

  // When a commodity is chosen, preselect its most-recorded variety/grade (forecasts need exactly one).
  // Runs once per mandi+commodity, so the user can still switch to "All varieties" afterwards.
  const autoPicked = useRef("");
  useEffect(() => {
    const key = `${value.market}|${value.commodity}`;
    const rows = varieties.data?.data;
    if (!rows?.length || !value.commodity || autoPicked.current === key) return;
    autoPicked.current = key;
    if (value.varietyGrade) return;
    const top = rows.reduce((a, b) => (b.observations > a.observations ? b : a));
    onChange({ ...value, varietyGrade: `${top.variety}||${top.grade}` });
  }, [varieties.data, value, onChange]);

  const set = (patch: Partial<Selection>) => onChange({ ...value, ...patch });

  if (states.isLoading) return <LoadingBlock label="Loading markets" />;
  if (states.isError) return <ErrorState error={states.error} title="Market list unavailable" />;

  // Show each mandi's last price date: AGMARKNET renamed many markets in Dec 2025, so old names stop then.
  const marketOptions = (markets.data?.data ?? []).map((m) => ({
    value: m.market,
    label: `${m.market}${value.district ? "" : ` (${m.district})`} · last ${formatDate(m.last_observation)}`,
  }));

  return (
    <form className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" onSubmit={(e) => e.preventDefault()} aria-label="Market selection">
      <SelectField
        label="State"
        placeholder="Select a state"
        value={value.state}
        options={opts(states.data?.data ?? [])}
        onChange={(state) => onChange({ ...value, state, district: "", market: "", commodity: "", varietyGrade: "" })}
      />
      <SelectField
        label="District"
        placeholder="All districts"
        value={value.district}
        options={opts(districts.data?.data ?? [])}
        disabled={!value.state}
        onChange={(district) => set({ district, market: "", commodity: "", varietyGrade: "" })}
      />
      <SelectField
        label="Mandi"
        placeholder={markets.isLoading ? "Loading…" : "Select a mandi"}
        value={value.market}
        options={marketOptions}
        disabled={!value.state}
        onChange={(market) => {
          const m = markets.data?.data.find((x) => x.market === market);
          set({ market, district: value.district || m?.district || "", commodity: "", varietyGrade: "" });
        }}
      />
      <SelectField
        label="Commodity"
        placeholder={commodities.isLoading ? "Loading…" : "Select a commodity"}
        value={value.commodity}
        options={(commodities.data?.data ?? []).map((c) => ({ value: c.commodity, label: `${c.commodity} · ${c.observations} obs` }))}
        disabled={!value.market}
        onChange={(commodity) => set({ commodity, varietyGrade: "" })}
      />
      <SelectField
        label="Variety / grade"
        placeholder="All varieties"
        value={value.varietyGrade}
        options={(varieties.data?.data ?? []).map((v) => ({
          value: `${v.variety}||${v.grade}`,
          label: `${v.variety || "Unspecified"}${v.grade ? ` · ${v.grade}` : ""} (${v.observations})`,
        }))}
        disabled={!value.commodity}
        onChange={(varietyGrade) => set({ varietyGrade })}
        hint="Preselected: the variety with the most price records. Forecasts need one variety and grade."
      />
      <DateField label="From" value={value.start} max={value.end || undefined} onChange={(start) => set({ start })} />
      <DateField label="To" value={value.end} min={value.start || undefined} onChange={(end) => set({ end })} />
    </form>
  );
}
