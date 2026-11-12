import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** Format an INR/quintal value. Returns an em dash for missing values (never a made-up number). */
export function formatPrice(value: number | null | undefined): string {
  return value == null || Number.isNaN(value) ? "—" : `₹${inr.format(value)}`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  return value == null || Number.isNaN(value)
    ? "—"
    : new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(value);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
