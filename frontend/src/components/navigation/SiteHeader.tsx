import { Menu, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { Logo } from "@/components/navigation/Logo";
import { Button } from "@/components/ui/button";
import { nav } from "@/lib/site";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { pathname } = useLocation();
  const overHero = pathname === "/" && !scrolled;

  useEffect(() => {
    setOpen(false);
  }, [pathname]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-[background-color,box-shadow,color] duration-500",
        overHero && !open ? "text-paper" : "bg-paper/90 text-charcoal shadow-[0_1px_0_var(--color-line)] backdrop-blur-md",
      )}
    >
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:rounded-md focus:bg-paper focus:px-3 focus:py-2 focus:text-forest">
        Skip to content
      </a>
      <div className="container-site flex h-16 items-center justify-between gap-6 md:h-20">
        <Link to="/" aria-label="Kisan Cold Link home" className="shrink-0">
          <Logo light={overHero && !open} />
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-current/10" : "opacity-80 hover:bg-current/5 hover:opacity-100",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden items-center gap-2 lg:flex">
          <Button asChild size="sm" variant="ghost" className={overHero ? "text-paper hover:bg-paper/10" : ""}>
            <Link to="/admin">Admin portal</Link>
          </Button>
          <Button asChild size="sm" variant={overHero ? "light" : "primary"}>
            <Link to="/contact">Request a demo</Link>
          </Button>
        </div>
        <button
          type="button"
          className="-mr-2 inline-flex size-11 items-center justify-center rounded-full lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>
      <AnimatePresence>
        {open && (
          <motion.nav
            id="mobile-nav"
            aria-label="Mobile"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t border-line bg-paper lg:hidden"
          >
            <ul className="container-site flex flex-col py-4">
              {nav.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      cn("block border-b border-line/70 py-4 font-display text-2xl", isActive ? "text-forest" : "text-charcoal")
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
              <li>
                <NavLink to="/admin" className={({ isActive }) => cn("block py-4 font-display text-2xl", isActive ? "text-forest" : "text-charcoal")}>
                  Admin portal
                </NavLink>
              </li>
            </ul>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
