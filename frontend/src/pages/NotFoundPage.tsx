import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <section className="container-site flex min-h-[70svh] flex-col items-start justify-center pt-24">
      <title>Page not found — Kisan Cold Link</title>
      <p className="eyebrow">404</p>
      <h1 className="mt-4 text-5xl font-medium">This page does not exist.</h1>
      <Button asChild className="mt-8">
        <Link to="/">Back to home</Link>
      </Button>
    </section>
  );
}
