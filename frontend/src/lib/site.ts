/** Public site configuration. Empty values mean "not configured yet" and are rendered honestly. */
const env = import.meta.env;

export const site = {
  name: "Kisan Cold Link",
  tagline: "Preserving Produce. Powering Possibilities.",
  url: env.VITE_SITE_URL ?? "",
  contactEmail: env.VITE_CONTACT_EMAIL ?? "",
  partnershipEmail: env.VITE_PARTNERSHIP_EMAIL || env.VITE_CONTACT_EMAIL || "",
  social: [
    { label: "LinkedIn", href: env.VITE_LINKEDIN_URL ?? "" },
    { label: "X", href: env.VITE_X_URL ?? "" },
    { label: "Instagram", href: env.VITE_INSTAGRAM_URL ?? "" },
  ].filter((s) => s.href),
};

export const nav = [
  { to: "/about", label: "About" },
  { to: "/technology", label: "Technology" },
  { to: "/market-intelligence", label: "Market Intelligence" },
  { to: "/research", label: "Research" },
  { to: "/contact", label: "Contact" },
] as const;
