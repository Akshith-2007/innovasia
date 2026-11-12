import { Link } from "react-router-dom";

import { Logo } from "@/components/navigation/Logo";
import { nav, site } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="bg-forest-deep text-paper/80">
      <div className="container-site grid gap-12 py-16 md:grid-cols-[1.4fr_1fr_1fr]">
        <div className="max-w-sm">
          <Logo light className="text-paper" />
          <p className="mt-5 text-sm leading-relaxed">
            {site.tagline} An AgriTech initiative exploring thermal-storage cooling and market intelligence built on
            government-published market data.
          </p>
        </div>
        <div>
          <h2 className="eyebrow text-amber-soft!">Explore</h2>
          <ul className="mt-4 space-y-2.5 text-sm">
            {nav.map((n) => (
              <li key={n.to}>
                <Link className="hover:text-paper" to={n.to}>
                  {n.label}
                </Link>
              </li>
            ))}
            <li>
              <Link className="hover:text-paper" to="/admin">
                Admin portal
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h2 className="eyebrow text-amber-soft!">Data</h2>
          <p className="mt-4 text-sm leading-relaxed">
            Market prices: AGMARKNET records from data.gov.in or a labelled public Kaggle copy of them (GODL licence).
            Every figure on this site carries its source and observation date.
          </p>
        </div>
      </div>
      <div className="border-t border-paper/10">
        <div className="container-site flex flex-col gap-2 py-6 text-xs text-paper/60 sm:flex-row sm:justify-between">
          <p>© {new Date().getFullYear()} Kisan Cold Link</p>
          <p>Cooling performance figures are design objectives, not measured results.</p>
        </div>
      </div>
    </footer>
  );
}
