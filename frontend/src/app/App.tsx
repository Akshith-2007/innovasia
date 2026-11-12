import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "@/components/layout/Layout";
import HomePage from "@/pages/HomePage";
import RouteErrorPage from "@/pages/RouteErrorPage";

const AboutPage = lazy(() => import("@/pages/AboutPage"));
const TechnologyPage = lazy(() => import("@/pages/TechnologyPage"));
const MarketIntelligencePage = lazy(() => import("@/pages/MarketIntelligencePage"));
const ResearchPage = lazy(() => import("@/pages/ResearchPage"));
const ContactPage = lazy(() => import("@/pages/ContactPage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));
const AdminPage = lazy(() => import("@/pages/AdminPage"));

export const routes = [
  {
    element: <Layout />,
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/about", element: <AboutPage /> },
      { path: "/technology", element: <TechnologyPage /> },
      { path: "/market-intelligence", element: <MarketIntelligencePage /> },
      { path: "/research", element: <ResearchPage /> },
      { path: "/contact", element: <ContactPage /> },
      { path: "/admin", element: <AdminPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

const router = createBrowserRouter(routes);

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60_000, refetchOnWindowFocus: false, retry: 1 } },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
