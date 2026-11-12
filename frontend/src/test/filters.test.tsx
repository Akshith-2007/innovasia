import { screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { MarketFilters } from "@/components/market/MarketFilters";
import type { Selection } from "@/hooks/useMarketData";
import { renderWithProviders, stubFetch } from "@/test/render";

afterEach(() => vi.unstubAllGlobals());

let latest: Selection | null = null;
function Harness() {
  const [sel, setSel] = useState<Selection>({ state: "S", district: "D", market: "M", commodity: "Potato", varietyGrade: "", start: "", end: "" });
  latest = sel;
  return <MarketFilters value={sel} onChange={setSel} />;
}

describe("MarketFilters", () => {
  it("preselects the variety/grade with the most records", async () => {
    // TEST VALUES: shapes of discovery endpoints
    stubFetch((path) => {
      if (path.startsWith("/commodities/Potato/varieties"))
        return { body: { data: [{ variety: "Potato", grade: "Large", observations: 3 }, { variety: "Potato", grade: "FAQ", observations: 243 }], meta: {} } };
      if (path.startsWith("/markets/states")) return { body: { data: ["S"], meta: {} } };
      return { body: { data: [], meta: {} } };
    });
    renderWithProviders(<Harness />);
    await waitFor(() => expect(latest?.varietyGrade).toBe("Potato||FAQ"));
    expect(screen.getByText(/Preselected: the variety with the most price records/)).toBeInTheDocument();
  });
});
