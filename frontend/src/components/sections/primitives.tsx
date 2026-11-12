import { motion } from "motion/react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Section({
  id,
  className,
  children,
  tone = "paper",
}: {
  id?: string;
  className?: string;
  children: ReactNode;
  tone?: "paper" | "deep" | "sage" | "forest";
}) {
  const tones = {
    paper: "bg-paper",
    deep: "bg-paper-deep",
    sage: "bg-sage-soft",
    forest: "bg-forest-deep text-paper [&_h2]:text-paper [&_h3]:text-paper",
  };
  return (
    <section id={id} className={cn("py-20 md:py-28", tones[tone], className)}>
      <div className="container-site">{children}</div>
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  lede,
  className,
  align = "left",
}: {
  eyebrow?: string;
  title: ReactNode;
  lede?: ReactNode;
  className?: string;
  align?: "left" | "center";
}) {
  return (
    <Reveal className={cn("max-w-3xl", align === "center" && "mx-auto text-center", className)}>
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h2 className="mt-4 text-3xl leading-[1.08] font-medium text-balance sm:text-4xl md:text-5xl">{title}</h2>
      {lede ? <p className="mt-5 text-base leading-relaxed text-muted text-pretty md:text-lg">{lede}</p> : null}
    </Reveal>
  );
}

export function Reveal({
  children,
  className,
  delay = 0,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: "div" | "li";
}) {
  const Tag = as === "li" ? motion.li : motion.div;
  return (
    <Tag
      className={className}
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </Tag>
  );
}

export function PageHero({ eyebrow, title, lede }: { eyebrow: string; title: ReactNode; lede?: ReactNode }) {
  return (
    <section className="relative overflow-hidden border-b border-line bg-paper pt-32 pb-16 md:pt-44 md:pb-24">
      <svg aria-hidden className="pointer-events-none absolute -right-24 bottom-0 h-full w-[60%] text-sage/50" viewBox="0 0 600 400" preserveAspectRatio="none">
        {Array.from({ length: 9 }).map((_, i) => (
          <path key={i} d={`M0 ${400 - i * 34} C 180 ${360 - i * 34}, 380 ${430 - i * 34}, 600 ${370 - i * 34}`} fill="none" stroke="currentColor" strokeWidth="1.2" />
        ))}
      </svg>
      <div className="container-site relative">
        <Reveal className="max-w-4xl">
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="mt-5 text-4xl leading-[1.04] font-medium text-balance sm:text-5xl md:text-6xl lg:text-7xl">{title}</h1>
          {lede ? <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted text-pretty">{lede}</p> : null}
        </Reveal>
      </div>
    </section>
  );
}

export function StatusTag({ status }: { status: "concept" | "prototype" | "live" | "planned" }) {
  const map = {
    concept: ["Concept", "bg-amber/15 text-amber-ink"],
    prototype: ["Prototype stage", "bg-sage-soft text-forest-deep"],
    live: ["Working on this site", "bg-forest text-paper"],
    planned: ["Planned", "bg-paper-deep text-muted"],
  } as const;
  const [label, cls] = map[status];
  return <span className={cn("inline-flex rounded-full px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-wider", cls)}>{label}</span>;
}
