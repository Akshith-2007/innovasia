export interface SourceInfo {
  dataset: string;
  name: string;
  publisher?: string[] | string | null;
  resource_id?: string | null;
  resource_url?: string | null;
  retrieved_at?: string | null;
  observation_range?: string[] | null;
  live: boolean;
  cached: boolean;
  third_party?: boolean;
  licence?: string | null;
  note?: string | null;
}

export interface Envelope<T> {
  data: T;
  source?: SourceInfo | null;
  meta: Record<string, unknown> & { live_error?: { code: string; message: string } };
}

export interface PriceRecord {
  state: string;
  district: string | null;
  market: string;
  commodity: string;
  variety: string | null;
  grade: string | null;
  arrival_date: string;
  min_price: number | null;
  max_price: number | null;
  modal_price: number;
  price_unit: string;
  source_kind?: "official" | "third_party_mirror" | null;
}

export interface MarketRow {
  state: string;
  district: string;
  market: string;
  observations: number;
  last_observation: string;
}

export interface CommodityRow {
  commodity: string;
  observations: number;
  markets: number;
}

export interface VarietyRow {
  variety: string;
  grade: string;
  observations: number;
}

export interface Metrics {
  n: number;
  mae: number;
  rmse: number;
  mape: number | null;
  directional_accuracy: number | null;
  n_moved: number;
}

export interface Prediction {
  series: Record<string, string>;
  latest_observation: { date: string; modal_price: number };
  prediction: {
    modal_price: number;
    unit: string;
    horizon: string;
    interval: { level: number; lower: number; upper: number; test_coverage: number } | null;
    interval_unavailable_reason: string | null;
  };
  model: {
    version: string;
    selected_model: string;
    trained_at: string;
    data_cutoff: string;
    test_metrics_overall: Metrics;
    test_metrics_series: { selected: Metrics; naive_last: Metrics } | null;
  };
  warnings: string[];
}

export interface ModelMetrics {
  model_version: string;
  selected_model: string;
  split: Record<string, string>;
  split_rows: Record<string, number>;
  results: Record<string, { type: "baseline" | "candidate"; validation: Metrics; test: Metrics }>;
  per_series_test: Array<Record<string, string> & { selected: Metrics; naive_last: Metrics }>;
  interval: { level: number; test_coverage: number; calibrated: boolean; method: string };
}

export interface ModelInfo {
  model_version: string;
  task: string;
  forecast_horizon: string;
  trained_at: string;
  data_cutoff: string;
  training_dataset: { path: string; sha256: string; rows: number };
  feature_schema: { features: string[]; categorical: string[]; target: string };
  config: { min_observations: number };
  eligible_series_count: number;
}

export interface Health {
  status: string;
  api_key_configured: boolean;
  data: { market_prices: boolean; crop_production: boolean };
  model: { available: boolean; version: string | null };
}

export interface SourcesDoc {
  sources: Array<{
    dataset: string;
    processed_file: string | null;
    resource_ids: string[];
    resource_url: string | null;
    source_kinds?: string[];
    source_names?: string[];
    licences?: string[];
    publisher: string[] | string | null;
    last_retrieved_at: string | null;
    observation_range: string[] | null;
    runs: Array<{ run_id: string; record_count: number | null; retrieved_at: string; complete: boolean | null }>;
  }>;
  quality: Record<string, Record<string, unknown>> | null;
}

export interface TrendRow {
  period: string;
  modal_mean: number;
  modal_median: number;
  min_price: number | null;
  max_price: number | null;
  observations: number;
  markets: number;
}

export interface ProductionRow {
  year: number;
  production_unit: string;
  area_ha: number | null;
  production: number | null;
  districts: number;
  yield_per_ha?: number | null;
}

export interface DistrictRow {
  district: string;
  production_unit: string;
  area_ha: number | null;
  production: number | null;
  yield_per_ha: number | null;
}
