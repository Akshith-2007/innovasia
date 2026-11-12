import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { routes } from "@/app/App";

function renderRoute(path: string) {
  vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("public pages render", () => {
  it.each([
    ["/", /Preserving Produce/],
    ["/about", /missing link/],
    ["/technology", /stored, carried and measured/],
    ["/market-intelligence", /Official mandi prices/],
    ["/research", /How the forecast is built/],
    ["/contact", /talk about the cold chain/],
  ])("%s", async (path, heading) => {
    renderRoute(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading }, { timeout: 8000 })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /skip to content/i })).toBeInTheDocument();
  }, 20_000); // lazy route + charts can exceed the 5 s default on a busy machine

  it("contact page does not invent an email address", async () => {
    renderRoute("/contact");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getAllByText("Email address being set up.").length).toBeGreaterThan(0);
    expect(document.querySelector('a[href^="mailto:"]')).toBeNull();
  });
});
