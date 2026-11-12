import { ErrorState, LoadingBlock } from "@/components/layout/States";
import { PageHero, Reveal, Section, SectionHeading } from "@/components/sections/primitives";
import { Badge } from "@/components/ui/card";
import { useModelInfo, useModelMetrics, useSources } from "@/hooks/useMarketData";
import { formatDate, formatNumber, formatPrice } from "@/lib/utils";

const NAMES: Record<string, string> = {
  naive_last: "Last observation (baseline)",
  moving_average_7: "7-obs moving average (baseline)",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
};

const method = [
  ["Data preparation", "Raw API pages are stored byte-for-byte with checksums. Records without a parseable date or a positive modal price are excluded and counted. Missing prices are never filled. Suspicious rows (min above max, modal outside range, likely unit errors) are flagged and kept out of training."],
  ["Feature engineering", "Mandi series are irregular, so lags are by observation (1, 3, 7, 14, 30), with explicit day-gap features, rolling means and volatility, price spread, month seasonality and series identifiers. Every feature uses only data up to the forecast origin."],
  ["Target", "The modal price at the next reported observation, if it falls within 7 days. The model learns the log change from the latest price."],
  ["Training methodology", "Chronological split by target date: earliest 70% train, next 15% validation, latest 15% test. No shuffling. The model is chosen by validation MAE, refit on train and validation, then scored once on the untouched test period."],
  ["Baselines and candidates", "Last-observation and 7-observation moving-average baselines compete directly with Random Forest and XGBoost. A baseline can win, and if it does, it is what we serve."],
  ["Evaluation", "MAE and RMSE in INR per quintal, MAPE, and directional accuracy on rows where the price actually moved. Prediction intervals are shown only if their test-period coverage matches the stated level."],
];

const limitations = [
  "Forecasts cover only series with at least 120 clean observations; others return an explanation instead of a number.",
  "The model sees prices only. Weather, arrivals and policy shocks are not modelled.",
  "Historical training data currently comes from a public Kaggle copy of AGMARKNET (GODL licence), not directly from data.gov.in; official downloads take precedence wherever both exist.",
  "Coverage is limited to Telangana and Andhra Pradesh by configuration.",
  "District production statistics are annual aggregates and are never used as farm-level yield.",
];

export default function ResearchPage() {
  return (
    <>
      <title>Research & ML — Kisan Cold Link</title>
      <PageHero eyebrow="Research & ML" title="How the forecast is built, and how well it actually does." lede="Methodology, data provenance and evaluation metrics, read live from the backend's saved model metadata." />

      <Section>
        <SectionHeading eyebrow="Dataset sources" title="Where the data comes from" />
        <Sources />
      </Section>

      <Section tone="deep">
        <SectionHeading eyebrow="Methodology" title="From raw records to a forecast" />
        <div className="mt-12 grid gap-px overflow-hidden rounded-card border border-line bg-line md:grid-cols-2">
          {method.map(([t, b], i) => (
            <Reveal key={t} delay={i * 0.04} className="bg-paper p-7">
              <h3 className="text-xl font-medium">{t}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted">{b}</p>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section>
        <SectionHeading eyebrow="Evaluation" title="Measured on the held-out test period" />
        <MetricsTable />
      </Section>

      <Section tone="sage">
        <SectionHeading eyebrow="Limitations" title="What this model does not do" />
        <ul className="mt-10 grid gap-4 md:grid-cols-2">
          {limitations.map((l) => (
            <li key={l} className="rounded-card bg-paper p-6 text-ink">{l}</li>
          ))}
        </ul>
      </Section>
    </>
  );
}

function Sources() {
  const q = useSources();
  if (q.isLoading) return <LoadingBlock />;
  if (q.isError) return <ErrorState error={q.error} className="mt-8" />;
  const sources = q.data!.sources;
  const mq = q.data!.quality?.market_prices as Record<string, unknown> | undefined;
  return (
    <div className="mt-10 space-y-6">
      {sources.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line p-6 text-sm text-muted">
          No official datasets have been downloaded yet. Planned sources: AGMARKNET mandi prices (data.gov.in resource
          9ef84268-d588-465a-a308-a864a43d0070 and the historical variety-wise resource) and district-wise season-wise crop
          production statistics.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-card border border-line bg-white" tabIndex={0} role="region" aria-label="Dataset sources table (scrolls horizontally)">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-line bg-paper-deep text-xs tracking-wider text-muted uppercase">
              <tr>
                <th className="px-5 py-3">Dataset</th>
                <th className="px-5 py-3">Resource</th>
                <th className="px-5 py-3">Observations</th>
                <th className="px-5 py-3">Retrieved</th>
                <th className="px-5 py-3">Runs</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.dataset} className="border-b border-line/60 last:border-0">
                  <td className="px-5 py-4 font-medium">
                    {s.dataset === "agmarknet" ? "AGMARKNET mandi prices" : "Crop production statistics"}
                    {s.source_kinds?.includes("third_party_mirror") ? (
                      <Badge tone="concept" className="mt-1.5 flex w-fit">Kaggle mirror</Badge>
                    ) : null}
                    {s.licences?.length ? <span className="mt-1 block text-xs font-normal text-muted">{s.licences[0].split(",")[0]}</span> : null}
                  </td>
                  <td className="px-5 py-4 font-mono text-xs break-all">{s.resource_ids.join(", ")}</td>
                  <td className="px-5 py-4">{s.observation_range ? `${s.observation_range[0]} → ${s.observation_range[1]}` : "—"}</td>
                  <td className="px-5 py-4">{formatDate(s.last_retrieved_at)}</td>
                  <td className="px-5 py-4 tabular">{s.runs.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {mq ? (
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Raw records", mq.input_records],
            ["After validation", mq.output_records],
            ["Mandis", mq.markets],
            ["Price series", mq.series],
          ].map(([k, v]) => (
            <div key={String(k)} className="rounded-xl border border-line bg-white p-5">
              <dt className="text-xs text-muted">{String(k)}</dt>
              <dd className="mt-1 font-display text-3xl tabular">{formatNumber(v as number)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

function MetricsTable() {
  const metrics = useModelMetrics();
  const info = useModelInfo();
  if (metrics.isLoading) return <LoadingBlock />;
  if (metrics.isError) return <ErrorState error={metrics.error} className="mt-8" title="No evaluated model yet" />;
  const m = metrics.data!.data;
  const i = info.data?.data;
  return (
    <div className="mt-10 space-y-6">
      <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm text-muted">
        <span>Version <span className="font-mono text-xs text-ink">{m.model_version}</span></span>
        {i ? <span>Trained {formatDate(i.trained_at)} · data cutoff {formatDate(i.data_cutoff)}</span> : null}
        <span>Test period {m.split.test_start} → {m.split.test_end} ({formatNumber(m.split_rows.test)} forecasts)</span>
        {i ? <span>{i.eligible_series_count} eligible series (≥ {i.config.min_observations} observations)</span> : null}
      </div>
      <div className="overflow-x-auto rounded-card border border-line bg-white" tabIndex={0} role="region" aria-label="Model metrics table (scrolls horizontally)">
        <table className="w-full min-w-[680px] text-left text-sm">
          <caption className="sr-only">Validation and test metrics per model</caption>
          <thead className="border-b border-line bg-paper-deep text-xs tracking-wider text-muted uppercase">
            <tr>
              <th className="px-5 py-3">Model</th>
              <th className="px-5 py-3 text-right">Val MAE</th>
              <th className="px-5 py-3 text-right">Test MAE</th>
              <th className="px-5 py-3 text-right">Test RMSE</th>
              <th className="px-5 py-3 text-right">Test MAPE</th>
              <th className="px-5 py-3 text-right">Direction</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(m.results).map(([name, r]) => (
              <tr key={name} className="border-b border-line/60 last:border-0">
                <td className="px-5 py-4 font-medium">
                  {NAMES[name] ?? name} {name === m.selected_model ? <Badge tone="live" className="ml-2">Selected</Badge> : null}
                </td>
                <td className="px-5 py-4 text-right tabular">{formatPrice(r.validation.mae)}</td>
                <td className="px-5 py-4 text-right tabular">{formatPrice(r.test.mae)}</td>
                <td className="px-5 py-4 text-right tabular">{formatPrice(r.test.rmse)}</td>
                <td className="px-5 py-4 text-right tabular">{r.test.mape != null ? `${formatNumber(r.test.mape, 2)}%` : "—"}</td>
                <td className="px-5 py-4 text-right tabular">
                  {r.test.directional_accuracy != null ? `${formatNumber(r.test.directional_accuracy * 100, 1)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-sm text-muted">
        MAE/RMSE in INR per quintal. Direction = share of moved prices where the forecast moved the same way (baselines that
        predict no change score 0%). Prediction interval: {m.interval.calibrated ? "calibrated" : "not calibrated, so not shown"} (
        {formatNumber(m.interval.test_coverage * 100, 1)}% test coverage at {Math.round(m.interval.level * 100)}% nominal).
      </p>
    </div>
  );
}
