import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/services/api";
import type {
  CommodityRow,
  DistrictRow,
  Health,
  MarketRow,
  ModelInfo,
  ModelMetrics,
  Prediction,
  PriceRecord,
  ProductionRow,
  SourcesDoc,
  TrendRow,
  VarietyRow,
} from "@/types/api";

export type Selection = {
  state: string;
  district: string;
  market: string;
  commodity: string;
  varietyGrade: string; // "variety||grade" or ""
  start: string;
  end: string;
};

export function splitVariety(v: string): { variety?: string; grade?: string } {
  if (!v) return {};
  const [variety, grade] = v.split("||");
  return { variety, grade };
}

export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: () => api.getRaw<Health>("/health"), staleTime: 30_000 });

export const useStates = () => useQuery({ queryKey: ["states"], queryFn: () => api.get<string[]>("/markets/states") });

export const useDistricts = (state: string) =>
  useQuery({
    queryKey: ["districts", state],
    queryFn: () => api.get<string[]>("/markets/districts", { state }),
    enabled: !!state,
  });

export const useMarkets = (state: string, district: string) =>
  useQuery({
    queryKey: ["markets", state, district],
    queryFn: () => api.get<MarketRow[]>("/markets/list", { state, district }),
    enabled: !!state,
  });

export const useCommodities = (state: string, district: string, market: string) =>
  useQuery({
    queryKey: ["commodities", state, district, market],
    queryFn: () => api.get<CommodityRow[]>("/commodities", { state, district, market }),
    enabled: !!state && !!market,
  });

export const useVarieties = (commodity: string, market: string) =>
  useQuery({
    queryKey: ["varieties", commodity, market],
    queryFn: () => api.get<VarietyRow[]>(`/commodities/${encodeURIComponent(commodity)}/varieties`, { market }),
    enabled: !!commodity && !!market,
  });

export const useLatestPrices = (s: Selection) =>
  useQuery({
    queryKey: ["prices", s.state, s.district, s.market, s.commodity],
    queryFn: () =>
      api.get<PriceRecord[]>("/market/prices", {
        state: s.state,
        district: s.district,
        market: s.market,
        commodity: s.commodity,
      }),
    enabled: !!s.state && !!s.market && !!s.commodity,
    retry: false,
  });

export const useHistory = (s: Selection) =>
  useQuery({
    queryKey: ["history", s],
    queryFn: () =>
      api.get<PriceRecord[]>("/market/history", {
        state: s.state,
        district: s.district,
        market: s.market,
        commodity: s.commodity,
        ...splitVariety(s.varietyGrade),
        start: s.start,
        end: s.end,
      }),
    enabled: !!s.state && !!s.market && !!s.commodity,
    retry: false,
  });

export const useCompare = (s: Selection) =>
  useQuery({
    queryKey: ["compare", s.state, s.commodity],
    queryFn: () => api.get<PriceRecord[]>("/market/compare", { state: s.state, commodity: s.commodity }),
    enabled: !!s.state && !!s.commodity,
    retry: false,
  });

export const useTrends = (s: Selection) =>
  useQuery({
    queryKey: ["trends", s.state, s.commodity],
    queryFn: () => api.get<TrendRow[]>("/market/trends", { state: s.state, commodity: s.commodity, freq: "M" }),
    enabled: !!s.state && !!s.commodity,
    retry: false,
  });

export const usePredict = () =>
  useMutation({
    mutationFn: (s: Selection) =>
      api.post<Prediction>("/ml/predict", {
        state: s.state,
        district: s.district || null,
        market: s.market,
        commodity: s.commodity,
        ...splitVariety(s.varietyGrade),
      }),
  });

export const useModelMetrics = () =>
  useQuery({ queryKey: ["ml-metrics"], queryFn: () => api.get<ModelMetrics>("/ml/metrics"), retry: false });

export const useModelInfo = () =>
  useQuery({ queryKey: ["ml-info"], queryFn: () => api.get<ModelInfo>("/ml/model-info"), retry: false });

export const useSources = () =>
  useQuery({ queryKey: ["sources"], queryFn: () => api.getRaw<SourcesDoc>("/data/sources"), retry: false });

export const useAgriOptions = () =>
  useQuery({
    queryKey: ["agri-options"],
    queryFn: () => api.get<{ states: string[]; crops: string[]; seasons: string[]; years: number[] }>("/agriculture/options"),
    retry: false,
  });

export const useProduction = (state: string, crop: string) =>
  useQuery({
    queryKey: ["production", state, crop],
    queryFn: () => api.get<ProductionRow[]>("/agriculture/yield", { state, crop }),
    enabled: !!state && !!crop,
    retry: false,
  });

export const useDistrictComparison = (state: string, crop: string) =>
  useQuery({
    queryKey: ["district-comparison", state, crop],
    queryFn: () => api.get<DistrictRow[]>("/agriculture/district-comparison", { state, crop }),
    enabled: !!state && !!crop,
    retry: false,
  });
