import { useState } from "react";

import { CompareChart } from "@/components/charts/CompareChart";
import { PriceHistoryChart } from "@/components/charts/PriceHistoryChart";
import { EmptyState, ErrorState, LoadingBlock, SourceNote } from "@/components/layout/States";
import { CropStatistics } from "@/components/market/CropStatistics";
import { ForecastPanel } from "@/components/market/ForecastPanel";
import { MarketFilters } from "@/components/market/MarketFilters";
import { PriceCards } from "@/components/market/PriceCards";
import { StateLivePrices } from "@/components/market/StateLivePrices";
import { StoragePlanner } from "@/components/market/StoragePlanner";
import { PageHero, Section } from "@/components/sections/primitives";
import { type Selection, useCompare, useHealth, useHistory } from "@/hooks/useMarketData";
import { formatNumber } from "@/lib/utils";

const EMPTY: Selection = { state: "", district: "", market: "", commodity: "", varietyGrade: "", start: "", end: "" };

export default function MarketIntelligencePage() {
  const [sel, setSel] = useState<Selection>(EMPTY);
  return (
    <>
      <title>Market Intelligence — Kisan Cold Link</title>
      <PageHero
        eyebrow="Market intelligence"
        title="Official mandi prices, history and forecasts."
        lede="Every number below is an AGMARKNET market record, shown with its observation date and source: either downloaded from data.gov.in or taken from a public Kaggle copy of it, labelled wherever it appears. Prices are in INR per quintal."
      />
      <StatusBar />
      <section className="sticky top-16 z-30 border-b border-line bg-paper/95 backdrop-blur md:top-20">
        <div className="container-site py-5">
          <MarketFilters value={sel} onChange={setSel} />
        </div>
      </section>

      <Block id="latest" title="Latest published prices" lede="Today's prices from data.gov.in when available; otherwise the most recent stored official observation, clearly labelled.">
        <PriceCards selection={sel} />
      </Block>

      <Block id="today" title="Today's prices across the state" lede="Every mandi price published today for the selected state, live from data.gov.in. Refreshes every 15 minutes." tone="sage">
        <StateLivePrices state={sel.state} />
      </Block>

      <Block id="history" title="Price history" lede="Actual observations only. Days without a published price are left as gaps, never filled in." tone="deep">
        <History selection={sel} />
      </Block>

      <Block id="compare" title="Compare mandis" lede="Latest observation per mandi in the selected state for this commodity. Each bar carries its own date.">
        <Compare selection={sel} />
      </Block>

      <Block id="forecast" title="Price forecast: next 7, 14 and 30 days" lede="Expected modal price in one, two and four weeks, drawn after the last 90 days of recorded prices, with the range that held in testing and each horizon's measured error." tone="sage">
        <ForecastPanel selection={sel} />
      </Block>

      <Block id="planner" title="Sell now or store?" lede="Enter your quantity and costs, choose how you would store, and compare selling today with selling after 7, 14 or 30 days. Storage defaults come from cited public sources and can all be changed.">
        <StoragePlanner selection={sel} />
      </Block>

      <Block id="production" tone="deep" title="District crop production" lede="Annual district statistics from the official crop production dataset. These are aggregates, not farm-level yields.">
        <CropStatistics />
      </Block>
    </>
  );
}

function Block({ id, title, lede, children, tone = "paper" }: { id: string; title: string; lede: string; children: React.ReactNode; tone?: "paper" | "deep" | "sage" }) {
  return (
    <Section id={id} tone={tone} className="py-14 md:py-20">
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-medium md:text-4xl">{title}</h2>
        <p className="mt-3 text-muted">{lede}</p>
      </div>
      {children}
    </Section>
  );
}

function StatusBar() {
  const h = useHealth();
  if (h.isLoading) return null;
  if (h.isError) return <div className="container-site pt-6"><ErrorState error={h.error} title="Backend unavailable" /></div>;
  const d = h.data!;
  const missing = [
    !d.data.market_prices && "historical market data not yet downloaded",
    !d.model.available && "no trained model yet",
    !d.api_key_configured && "live daily prices off (no API key configured)",
  ].filter(Boolean);
  if (!missing.length) return null;
  return (
    <div className="container-site pt-6">
      <p className="rounded-xl border border-amber/30 bg-amber/10 px-4 py-3 text-sm text-amber-ink" role="status">
        Setup in progress: {missing.join("; ")}. Sections that depend on these will explain what is missing instead of showing numbers.
      </p>
    </div>
  );
}

function History({ selection }: { selection: Selection }) {
  const q = useHistory(selection);
  if (!selection.commodity) return <EmptyState>Select a commodity to plot its history.</EmptyState>;
  if (q.isLoading) return <LoadingBlock label="Loading history" />;
  if (q.isError) return <ErrorState error={q.error} />;
  const rows = q.data!.data;
  const mixed = new Set(rows.map((r) => `${r.variety}|${r.grade}`)).size > 1;
  return (
    <div className="rounded-card border border-line bg-paper p-4 md:p-6">
      <p className="mb-4 text-sm text-muted">
        {formatNumber(rows.length)} observations
        {mixed ? " · several varieties/grades combined — pick one above for a single series" : ""}
      </p>
      <PriceHistoryChart rows={rows} />
      <SourceNote source={q.data!.source} className="mt-4" />
    </div>
  );
}

function Compare({ selection }: { selection: Selection }) {
  const q = useCompare(selection);
  if (!selection.commodity) return <EmptyState>Select a commodity to compare mandis.</EmptyState>;
  if (q.isLoading) return <LoadingBlock label="Comparing mandis" />;
  if (q.isError) return <ErrorState error={q.error} />;
  return (
    <div className="rounded-card border border-line bg-white p-4 md:p-6">
      <CompareChart rows={q.data!.data} highlight={selection.market} />
      <SourceNote source={q.data!.source} className="mt-4" />
    </div>
  );
}
