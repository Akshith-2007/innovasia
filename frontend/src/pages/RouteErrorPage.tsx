import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";

/** Shown if a page throws. Never shows data; just explains and offers a way back. */
export default function RouteErrorPage() {
  const error = useRouteError();
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : "Unknown error";
  return (
    <main className="container-site flex min-h-svh flex-col items-start justify-center">
      <title>Something went wrong — Kisan Cold Link</title>
      <p className="eyebrow">Error</p>
      <h1 className="mt-4 text-4xl font-medium md:text-5xl">This page could not be displayed.</h1>
      <p className="mt-4 max-w-xl text-muted">Please reload the page. If the problem continues, the details below help us fix it.</p>
      <pre className="mt-6 max-w-full overflow-x-auto rounded-xl bg-paper-deep p-4 text-xs text-ink">{message}</pre>
      <Button asChild className="mt-8">
        <Link to="/">Back to home</Link>
      </Button>
    </main>
  );
}
