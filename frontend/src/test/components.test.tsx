import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PriceHistoryChart } from "@/components/charts/PriceHistoryChart";
import { ErrorState, SourceNote } from "@/components/layout/States";
import { ForecastPanel } from "@/components/market/ForecastPanel";
import { PriceCards } from "@/components/market/PriceCards";
import { formatPrice } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { renderWithProviders, stubFetch } from "@/test/render";

const SEL = { state: "S", district: "D", market: "M", commodity: "C", varietyGrade: "", start: "", end: "" };

afterEach(() => vi.unstubAllGlobals());

describe("formatting", () => {
  it("never invents a value for missing prices", () => {
    expect(formatPrice(null)).toBe("—");
    expect(formatPrice(undefined)).toBe("—");
    expect(formatPrice(1234)).toBe("₹1,234");
  });
});

describe("ErrorState", () => {
  it("shows the API message and a setup hint", () => {
    renderWithProviders(<ErrorState error={new ApiError("market_prices.parquet missing", "data_unavailable", 503)} />);
    expect(screen.getByRole("alert")).toHaveTextContent("market_prices.parquet missing");
    expect(screen.getByRole("alert")).toHaveTextContent("Official data has not been imported yet");
  });
});

describe("SourceNote", () => {
  it("labels stored data as stored, not live", () => {
    renderWithProviders(
      <SourceNote source={{ dataset: "agmarknet", name: "AGMARKNET", live: false, cached: true, observation_range: ["2024-01-01", "2024-02-01"] }} />,
    );
    expect(screen.getByText("Stored official data")).toBeInTheDocument();
    expect(screen.queryByText(/Live/)).not.toBeInTheDocument();
  });
});

describe("PriceCards", () => {
  it("shows an error and no prices when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    renderWithProviders(<PriceCards selection={SEL} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent("not reachable");
    expect(screen.queryByTestId("price-card")).toBeNull();
    expect(document.body.textContent).not.toMatch(/₹\d/);
  });

  it("renders source-tagged cards and the live-fallback notice", async () => {
    stubFetch(() => ({
      body: {
        data: [{ state: "S", district: "D", market: "M", commodity: "C", variety: "V", grade: "FAQ", arrival_date: "2024-03-01", min_price: 900, max_price: 1100, modal_price: 1000, price_unit: "INR/quintal" }],
        source: { dataset: "agmarknet", name: "AGMARKNET", live: false, cached: true },
        meta: { live_error: { code: "not_configured", message: "DATA_GOV_API_KEY is not configured." } },
      },
    }));
    renderWithProviders(<PriceCards selection={SEL} />);
    expect(await screen.findByTestId("price-card")).toHaveTextContent("₹1,000");
    expect(screen.getByTestId("price-card")).toHaveTextContent("1 Mar 2024");
    expect(screen.getByRole("status")).toHaveTextContent("Showing the latest stored observations instead");
  });
});

describe("ForecastPanel", () => {
  it("explains insufficient data instead of showing a number", async () => {
    stubFetch(() => ({
      status: 422,
      body: { error: { code: "insufficient_data", message: "This series did not have enough official history", details: {} } },
    }));
    renderWithProviders(<ForecastPanel selection={SEL} />);
    await waitFor(() => expect(screen.getAllByRole("alert")[0]).toHaveTextContent("not have enough official history"));
    expect(screen.queryByTestId("forecast-result")).toBeNull();
    expect(document.body.textContent).not.toMatch(/₹\d/);
  });

  it("shows only multi-day forecasts with ranges and test error", async () => {
    // TEST VALUES: shape of /decision/forecast-horizons
    stubFetch((path) =>
      path.startsWith("/decision/forecast-horizons")
        ? {
            body: {
              data: {
                latest_observation: { date: new Date().toISOString().slice(0, 10), modal_price: 1000 },
                model_version: "v",
                data_cutoff: "2026-01-01",
                horizons: [
                  { horizon_days: 7, available: true, target_date_window: ["2026-01-08", "2026-01-11"], modal_price: 1100, beats_naive_on_test: true,
                    interval: { level: 0.8, lower: 900, upper: 1300, test_coverage: 0.8 }, test_metrics_overall: { mae: 1, mape: 14.3, directional_accuracy: 0.6 }, test_metrics_series: null },
                  { horizon_days: 30, available: true, target_date_window: ["2026-01-31", "2026-02-03"], modal_price: 950, beats_naive_on_test: false,
                    interval: null, test_metrics_overall: { mae: 1, mape: 20.8, directional_accuracy: 0.6 }, test_metrics_series: null },
                ],
              },
              meta: {},
            },
          }
        : { body: { data: [], meta: {} } },
    );
    renderWithProviders(<ForecastPanel selection={SEL} />);
    const result = await screen.findByTestId("forecast-result");
    expect(result).toHaveTextContent("In 7 days");
    expect(result).toHaveTextContent("₹1,100");
    expect(result).toHaveTextContent("▲ 10% vs latest");
    expect(result).toHaveTextContent("Likely ₹900 – ₹1,300");
    expect(result).toHaveTextContent("weak forecast"); // 30-day horizon did not beat the baseline
    expect(result).not.toHaveTextContent("next reported observation");
  });
});

describe("PriceHistoryChart", () => {
  it("renders an accessible chart container for real rows", () => {
    renderWithProviders(
      <PriceHistoryChart
        rows={[{ state: "S", district: "D", market: "M", commodity: "C", variety: null, grade: null, arrival_date: "2024-01-01", min_price: 1, max_price: 3, modal_price: 2, price_unit: "INR/quintal" }]}
      />,
    );
    expect(screen.getByRole("img", { name: /1 observations/ })).toBeInTheDocument();
  });
});
