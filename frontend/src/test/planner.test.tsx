import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StoragePlanner } from "@/components/market/StoragePlanner";
import { renderWithProviders, stubFetch } from "@/test/render";

const SEL = { state: "S", district: "", market: "M", commodity: "Tomato", varietyGrade: "", start: "", end: "" };
// TEST VALUES only: shape of /decision/storage-options
const OPTIONS = {
  data: {
    commodity: "Tomato",
    category: "perishable",
    options: [
      { id: "sell_now", name: "Sell now", description: "Sell at the mandi.", suited: true, default_cost_per_quintal_per_month: 0, default_loss_pct_per_30_days: 0, default_max_days: 0, notes: null, sources: [] },
      { id: "zecc", name: "Zero Energy Cool Chamber", description: "Evaporative chamber.", suited: true, default_cost_per_quintal_per_month: 0, default_loss_pct_per_30_days: null, default_max_days: 6, notes: null, sources: [{ title: "ICAR study", url: "https://example.org/icar", year: "x" }] },
    ],
  },
  meta: {},
};

afterEach(() => vi.unstubAllGlobals());

describe("StoragePlanner", () => {
  it("asks for the farmer's own loss estimate when no source exists, and shows the source", async () => {
    stubFetch((path) =>
      path.startsWith("/decision/storage-options")
        ? { body: OPTIONS }
        : { status: 422, body: { error: { code: "input_required", message: "No published loss figure for 'Zero Energy Cool Chamber'.", details: {} } } },
    );
    renderWithProviders(<StoragePlanner selection={SEL} />);
    fireEvent.change(await screen.findByLabelText("Storage option"), { target: { value: "zecc" } });
    expect(await screen.findByText(/No published loss figure was found/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ICAR study" })).toHaveAttribute("href", "https://example.org/icar");
    expect((screen.getByLabelText("Loss % per 30 days") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Keeps for (days)") as HTMLInputElement).value).toBe("6");
  });

  it("shows an explanation instead of numbers when the plan fails", async () => {
    stubFetch((path) =>
      path.startsWith("/decision/storage-options")
        ? { body: OPTIONS }
        : { status: 422, body: { error: { code: "insufficient_data", message: "This series did not have enough history", details: {} } } },
    );
    renderWithProviders(<StoragePlanner selection={SEL} />);
    fireEvent.change(await screen.findByLabelText("Storage option"), { target: { value: "sell_now" } });
    fireEvent.change(screen.getByLabelText("Quantity (quintals)"), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: /compare sell now vs store/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("not have enough history"));
    expect(screen.queryByTestId("plan-result")).toBeNull();
  });
});
