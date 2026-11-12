import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PAGES = [
  { path: "/", h1: /Preserving Produce/ },
  { path: "/about", h1: /missing link/ },
  { path: "/technology", h1: /stored, carried and measured/ },
  { path: "/market-intelligence", h1: /Official mandi prices/ },
  { path: "/research", h1: /How the forecast is built/ },
  { path: "/contact", h1: /talk about the cold chain/ },
  { path: "/admin", h1: /Chamber monitor/ },
];

const SHOTS = process.env.E2E_SCREENSHOT_DIR;

for (const p of PAGES) {
  test.describe(p.path, () => {
    test("renders, fits the viewport and passes axe", async ({ page }, info) => {
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.goto(p.path);
      await expect(page.getByRole("heading", { level: 1, name: p.h1 })).toBeVisible();
      await page.waitForLoadState("networkidle");

      // No horizontal page scroll at any breakpoint.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, "horizontal overflow in px").toBeLessThanOrEqual(1);

      // Reveal-on-scroll content: scroll through so everything is in its final state before axe.
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 500) {
          window.scrollTo({ top: y, behavior: "instant" });
          await new Promise((r) => setTimeout(r, 60));
        }
        window.scrollTo({ top: 0, behavior: "instant" });
      });
      await page.waitForTimeout(900);

      const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      const serious = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(
        serious.map((v) => `${v.id}: ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`),
      ).toEqual([]);
      expect(errors).toEqual([]);

      if (SHOTS) {
        await page.screenshot({ path: `${SHOTS}/${info.project.name}${p.path.replace(/\//g, "_") || "_home"}.png`, fullPage: true });
      }
    });
  });
}

test("primary navigation works", async ({ page, isMobile }) => {
  await page.goto("/");
  if (isMobile) {
    await page.getByRole("button", { name: "Open menu" }).click();
    await page.getByRole("navigation", { name: "Mobile" }).getByRole("link", { name: "Technology" }).click();
  } else {
    const viewport = page.viewportSize()!;
    test.skip(viewport.width < 1024, "tablet uses the mobile menu; covered above");
    await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Technology" }).click();
  }
  await expect(page).toHaveURL(/\/technology$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("stored, carried and measured");
});

const API = `http://127.0.0.1:${process.env.API_PORT ?? "8000"}/api/v1`;

test("market page: honest states without data, labelled prices with data", async ({ page, request }) => {
  const health = await (await request.get(`${API}/health`)).json();
  await page.goto("/market-intelligence");
  if (!health.data.market_prices) {
    await expect(page.getByText(/Setup in progress/)).toBeVisible();
    await expect(page.getByRole("alert").first()).toBeVisible();
    expect(await page.locator("main").innerText()).not.toMatch(/₹\s?\d/);
    return;
  }
  const states = (await (await request.get(`${API}/markets/states`)).json()).data as string[];
  const markets = (await (await request.get(`${API}/markets/list`, { params: { state: states[0] } })).json()).data;
  const m = markets.sort((a: { observations: number }, b: { observations: number }) => b.observations - a.observations)[0];
  const commodities = (
    await (await request.get(`${API}/commodities`, { params: { state: m.state, district: m.district, market: m.market } })).json()
  ).data;
  await page.getByLabel("State", { exact: true }).selectOption(m.state);
  await page.getByLabel("Mandi", { exact: true }).selectOption(m.market);
  await page.getByLabel("Commodity", { exact: true }).selectOption(commodities[0].commodity);
  const card = page.getByTestId("price-card").first();
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card).toContainText("₹");
  // Every visible price carries a source label and the section shows provenance.
  await expect(card.getByText(/Kaggle mirror|Stored|Live/)).toBeVisible();
  await expect(page.locator("#latest").getByText(/Observations|Retrieved/).first()).toBeVisible();
  await expect(page.getByRole("img", { name: /Modal price history/ })).toBeVisible();
});

test("research page: missing model explained, or real metrics shown", async ({ page, request }) => {
  const health = await (await request.get(`${API}/health`)).json();
  await page.goto("/research");
  if (!health.model.available) {
    await expect(page.getByText("No evaluated model yet")).toBeVisible();
    expect(await page.locator("main").innerText()).not.toMatch(/₹\s?\d/);
    return;
  }
  const table = page.getByRole("table").filter({ hasText: "Test MAE" });
  await expect(table).toBeVisible();
  await expect(table.getByText("Selected")).toBeVisible();
  await expect(page.getByText(health.model.version)).toBeVisible();
});

test("API key never reaches the browser bundle", async ({ page }) => {
  const scripts: string[] = [];
  page.on("response", async (r) => {
    if (r.url().includes("/src/") || r.url().endsWith(".js")) scripts.push(await r.text().catch(() => ""));
  });
  await page.goto("/market-intelligence");
  await page.waitForLoadState("networkidle");
  expect(scripts.join("\n")).not.toMatch(/DATA_GOV_API_KEY|api-key=/);
});
