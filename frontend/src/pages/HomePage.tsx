import { ArrowRight, ArrowUpRight, BarChart3, Droplets, Snowflake, Thermometer, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Hero } from "@/components/hero/Hero";
import { PcmDiagram, WaterLoopDiagram } from "@/components/sections/diagrams";
import { Reveal, Section, SectionHeading, StatusTag } from "@/components/sections/primitives";
import { Button } from "@/components/ui/button";

const problems = [
  ["Post-harvest loss", "Perishable produce degrades between harvest and sale when it cannot be kept cool."],
  ["Limited storage access", "Cold storage is often distant, costly or sized for large operators rather than smallholders."],
  ["Temperature instability", "Unreliable power and weak insulation let storage temperatures swing through the day."],
  ["Market uncertainty", "Mandi prices move daily, and the best time and place to sell is rarely obvious."],
  ["Information gaps", "Official market data exists, but it is hard to find, compare and interpret in the moment."],
];

const pillars = [
  {
    icon: Snowflake,
    title: "Smart cooling",
    body: "Thermal energy storage with phase-change materials and an independent water loop, designed to buffer produce against temperature swings.",
    points: ["Phase-change thermal storage", "Independent water circulation", "Temperature monitoring"],
  },
  {
    icon: BarChart3,
    title: "Agricultural intelligence",
    body: "Official AGMARKNET mandi prices and district crop statistics, processed transparently and paired with a genuinely trained forecast model.",
    points: ["Official mandi data", "Historical analysis", "Evaluated price forecasts"],
  },
  {
    icon: Users,
    title: "Farmer empowerment",
    body: "Making market and storage information accessible, so selling decisions can rest on evidence, with Telugu-first voice assistance on the roadmap.",
    points: ["Accessible market information", "Storage understanding", "Telugu-first voice (planned)"],
  },
];

const steps = [
  ["Harvest", "Produce leaves the field at its freshest."],
  ["Preserve", "Thermal storage holds a stable, cool environment."],
  ["Monitor", "Sensors track temperature and humidity."],
  ["Analyze", "Official market data is processed and modelled."],
  ["Decide", "Sell when and where the evidence points."],
];

const objectives = [
  "Reduce avoidable spoilage of perishables held near the farm.",
  "Keep storage temperature stable through power interruptions.",
  "Give farmers clear access to official mandi prices.",
  "Support selling decisions with transparent, evaluated forecasts.",
];

export default function HomePage() {
  return (
    <>
      <title>Kisan Cold Link — Preserving Produce. Powering Possibilities.</title>
      <Hero />

      {/* Problem */}
      <Section>
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
          <SectionHeading
            eyebrow="The problem"
            title="Good harvests still lose value after they leave the field."
            lede="The gap between harvest and sale is where storage, temperature and information decide what a crop is worth."
            className="lg:sticky lg:top-32 lg:self-start"
          />
          <ol className="divide-y divide-line border-y border-line">
            {problems.map(([title, body], i) => (
              <Reveal as="li" key={title} delay={i * 0.05} className="grid grid-cols-[3rem_1fr] gap-4 py-7 md:grid-cols-[4rem_1fr]">
                  <span className="font-display text-2xl text-amber-ink tabular">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3 className="text-xl font-medium md:text-2xl">{title}</h3>
                    <p className="mt-2 text-muted">{body}</p>
                  </div>
                </Reveal>
            ))}
          </ol>
        </div>
      </Section>

      {/* Solution */}
      <Section tone="forest">
        <SectionHeading
          eyebrow="Our approach"
          title={<span className="text-paper">Three pillars, one link from field to market.</span>}
          className="[&_.eyebrow]:text-amber-soft!"
        />
        <div className="mt-16 grid gap-px overflow-hidden rounded-card bg-paper/10 md:grid-cols-3">
          {pillars.map(({ icon: Icon, title, body, points }, i) => (
            <Reveal key={title} delay={i * 0.08} className="bg-forest-deep p-8 md:p-10">
              <Icon className="size-7 text-amber-soft" aria-hidden />
              <h3 className="mt-8 text-2xl font-medium md:text-3xl">{title}</h3>
              <p className="mt-4 leading-relaxed text-paper/75">{body}</p>
              <ul className="mt-6 space-y-2 text-sm text-paper/85">
                {points.map((p) => (
                  <li key={p} className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-amber-soft" aria-hidden /> {p}
                  </li>
                ))}
              </ul>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* How it works */}
      <Section>
        <SectionHeading eyebrow="How it works" title="Harvest → Preserve → Monitor → Analyze → Decide" />
        <div className="relative mt-16">
          <div className="absolute top-5 right-0 left-0 hidden h-px bg-line md:block" aria-hidden />
          <ol className="relative grid gap-10 md:grid-cols-5 md:gap-6">
          {steps.map(([title, body], i) => (
            <Reveal as="li" key={title} delay={i * 0.08} className="relative flex gap-5 md:block">
                <span className="relative z-10 flex size-10 shrink-0 items-center justify-center rounded-full border border-forest bg-paper font-display text-forest">
                  {i + 1}
                </span>
                <div>
                  <h3 className="text-xl font-medium md:mt-6">{title}</h3>
                  <p className="mt-2 text-sm text-muted">{body}</p>
                </div>
              </Reveal>
          ))}
        </ol>
        </div>
      </Section>

      {/* Product preview */}
      <Section tone="deep">
        <SectionHeading
          eyebrow="Product preview"
          title="Engineering the cold chain, explained honestly."
          lede="Each component is labelled with its real stage of development."
        />
        <div className="mt-16 grid gap-16">
          <PreviewRow
            status="concept"
            icon={Snowflake}
            title="PCM thermal storage"
            body="Phase-change material absorbs heat as it melts at a near-constant temperature, buffering the chamber when the cooling source is off."
            visual={<PcmDiagram />}
          />
          <PreviewRow
            reverse
            status="concept"
            icon={Droplets}
            title="Independent water circulation"
            body="A pump moves water from a reservoir through an aluminium coil in the chamber and back. The water carries cooling; a separate source re-cools it."
            visual={<WaterLoopDiagram />}
          />
          <div className="grid gap-6 md:grid-cols-3">
            <MiniPreview status="planned" icon={Thermometer} title="Temperature monitoring" body="Temperature and humidity sensing with future ESP32 integration." to="/technology" />
            <MiniPreview status="live" icon={BarChart3} title="Market intelligence" body="Official AGMARKNET prices, history and mandi comparisons." to="/market-intelligence" />
            <MiniPreview status="live" icon={ArrowUpRight} title="Price forecasting" body="Next-observation modal-price model with published evaluation." to="/research" />
          </div>
        </div>
      </Section>

      {/* Impact */}
      <Section>
        <div className="grid gap-12 lg:grid-cols-2">
          <SectionHeading
            eyebrow="Intended impact"
            title="What we are working toward."
            lede="These are objectives, not validated results. We will publish measured outcomes only once field trials produce them."
          />
          <ul className="grid gap-4 sm:grid-cols-2">
            {objectives.map((o, i) => (
              <Reveal as="li" key={o} delay={i * 0.06} className="h-full rounded-card border border-line bg-white/60 p-6">
                  <span className="eyebrow text-amber-ink!">Objective {i + 1}</span>
                  <p className="mt-3 text-lg leading-snug font-medium text-charcoal">{o}</p>
                </Reveal>
            ))}
          </ul>
        </div>
      </Section>

      {/* CTA */}
      <section className="bg-sage-soft">
        <div className="container-site py-24 text-center md:py-32">
          <Reveal>
            <h2 className="mx-auto max-w-3xl text-4xl leading-tight font-medium text-balance md:text-6xl">
              Let&apos;s build a smarter future for agricultural preservation.
            </h2>
            <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link to="/technology">
                  Explore Technology <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="text-forest">
                <Link to="/contact">Contact Us</Link>
              </Button>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

function PreviewRow({
  title,
  body,
  visual,
  status,
  icon: Icon,
  reverse,
}: {
  title: string;
  body: string;
  visual: React.ReactNode;
  status: "concept" | "prototype" | "live" | "planned";
  icon: typeof Snowflake;
  reverse?: boolean;
}) {
  return (
    <Reveal className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
      <div className={reverse ? "lg:order-2" : ""}>
        <div className="flex items-center gap-3">
          <Icon className="size-5 text-forest" aria-hidden />
          <StatusTag status={status} />
        </div>
        <h3 className="mt-5 text-3xl font-medium md:text-4xl">{title}</h3>
        <p className="mt-4 max-w-lg text-lg leading-relaxed text-muted">{body}</p>
      </div>
      <div className="rounded-card border border-line bg-paper p-5 md:p-8">{visual}</div>
    </Reveal>
  );
}

function MiniPreview({
  title,
  body,
  status,
  icon: Icon,
  to,
}: {
  title: string;
  body: string;
  status: "concept" | "prototype" | "live" | "planned";
  icon: typeof Snowflake;
  to: string;
}) {
  return (
    <Link to={to} className="group flex flex-col rounded-card border border-line bg-paper p-7 transition-colors hover:border-forest/40">
      <div className="flex items-center justify-between">
        <Icon className="size-5 text-forest" aria-hidden />
        <StatusTag status={status} />
      </div>
      <h3 className="mt-8 text-2xl font-medium">{title}</h3>
      <p className="mt-2 flex-1 text-sm text-muted">{body}</p>
      <span className="mt-6 inline-flex items-center gap-1 text-sm font-semibold text-forest">
        Learn more <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
      </span>
    </Link>
  );
}
