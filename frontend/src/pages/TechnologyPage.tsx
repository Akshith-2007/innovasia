import { Cpu, Database, Droplets, Gauge, LineChart, Server, Snowflake, Thermometer, Wind } from "lucide-react";

import { PcmDiagram, WaterLoopDiagram } from "@/components/sections/diagrams";
import { PageHero, Reveal, Section, SectionHeading, StatusTag } from "@/components/sections/primitives";

const tes = [
  ["Phase-change material (PCM)", "A material chosen to melt and freeze near the target storage temperature."],
  ["Latent heat", "While changing phase, the PCM absorbs or releases large amounts of heat with little temperature change."],
  ["Charging", "A cooling source removes heat from the PCM until it solidifies, storing cooling capacity."],
  ["Discharging", "Heat entering the chamber is absorbed as the PCM melts, holding the chamber near its set point."],
  ["Thermal buffering", "Stored capacity bridges periods when the cooling source is off or power is unavailable."],
  ["Insulation and duration", "Better insulation lowers heat gain, so the same stored capacity lasts longer. Duration depends on both."],
];

const monitoring = [
  { icon: Thermometer, title: "Temperature", body: "Chamber, PCM and water-loop temperatures show whether storage is holding its set point." },
  { icon: Wind, title: "Humidity", body: "Relative humidity matters for many perishables and is tracked alongside temperature." },
  { icon: Gauge, title: "Sensor placement", body: "Sensors at several heights and near the coil reveal stratification and uneven cooling." },
  { icon: Cpu, title: "Future ESP32 integration", body: "A low-cost microcontroller is planned to log readings and send them to the platform." },
];

const physical = [
  { name: "Insulated storage chamber", status: "concept" as const },
  { name: "PCM thermal storage modules", status: "concept" as const },
  { name: "Reservoir, pump and aluminium coil loop", status: "concept" as const },
  { name: "Separate re-cooling source", status: "concept" as const },
  { name: "Temperature / humidity sensors + ESP32", status: "planned" as const },
];

const software = [
  { icon: Database, name: "Official data pipeline (data.gov.in → validated Parquet)", status: "live" as const },
  { icon: Server, name: "FastAPI backend with source-tagged responses", status: "live" as const },
  { icon: LineChart, name: "Trained modal-price forecasting model", status: "live" as const },
  { icon: Thermometer, name: "Sensor telemetry ingestion", status: "planned" as const },
];

export default function TechnologyPage() {
  return (
    <>
      <title>Technology — Kisan Cold Link</title>
      <PageHero
        eyebrow="Technology"
        title="Cooling that is stored, carried and measured."
        lede="How thermal energy storage, an independent water loop and monitoring fit together, and which parts exist today."
      />

      <Section>
        <div className="grid items-start gap-12 lg:grid-cols-2 lg:gap-20">
          <div>
            <div className="flex items-center gap-3">
              <Snowflake className="size-5 text-forest" aria-hidden />
              <StatusTag status="concept" />
            </div>
            <SectionHeading className="mt-4" title="Thermal energy storage" lede="Storing cooling as latent heat, so the chamber stays stable even when the cooling source is not running." />
            <dl className="mt-10 divide-y divide-line border-y border-line">
              {tes.map(([term, def]) => (
                <div key={term} className="grid gap-1 py-5 sm:grid-cols-[13rem_1fr] sm:gap-6">
                  <dt className="font-semibold text-charcoal">{term}</dt>
                  <dd className="text-muted">{def}</dd>
                </div>
              ))}
            </dl>
          </div>
          <Reveal className="rounded-card border border-line bg-white/60 p-5 md:p-8 lg:sticky lg:top-32">
            <PcmDiagram />
          </Reveal>
        </div>
      </Section>

      <Section tone="deep">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_1.2fr] lg:gap-20">
          <div>
            <div className="flex items-center gap-3">
              <Droplets className="size-5 text-forest" aria-hidden />
              <StatusTag status="concept" />
            </div>
            <SectionHeading className="mt-4" title="Independent water circulation" />
            <p className="mt-6 font-display text-xl text-forest md:text-2xl">
              Water reservoir → Pump → Aluminium coil → Return reservoir
            </p>
            <div className="mt-6 space-y-4 text-lg leading-relaxed text-muted">
              <p>A pump draws chilled water from the reservoir and pushes it through an aluminium coil inside the chamber, where it absorbs heat before returning.</p>
              <p className="rounded-xl border-l-4 border-amber bg-paper p-4 text-base text-ink">
                Circulating water <strong>transports</strong> cooling. It does <strong>not generate</strong> it. A separate cooling source is required to re-cool the reservoir water.
              </p>
            </div>
          </div>
          <Reveal className="rounded-card border border-line bg-paper p-5 md:p-8">
            <WaterLoopDiagram />
          </Reveal>
        </div>
      </Section>

      <Section>
        <SectionHeading eyebrow="Monitoring" title="You cannot manage what you do not measure." />
        <div className="mt-14 grid gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {monitoring.map(({ icon: Icon, title, body }, i) => (
            <Reveal key={title} delay={i * 0.05} className="bg-paper p-7">
              <Icon className="size-5 text-forest" aria-hidden />
              <h3 className="mt-6 text-xl font-medium">{title}</h3>
              <p className="mt-2 text-sm text-muted">{body}</p>
            </Reveal>
          ))}
        </div>
        <p className="mt-6 text-sm text-muted">Monitoring hardware is planned. No live sensor readings are shown on this site.</p>
      </Section>

      <Section tone="sage">
        <SectionHeading eyebrow="System architecture" title="Two systems, shown separately." lede="The physical cooling system and the software platform are independent today. Status labels reflect what actually exists." />
        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          <ArchColumn title="Physical system">
            {physical.map((p) => (
              <ArchRow key={p.name} name={p.name} status={p.status} />
            ))}
          </ArchColumn>
          <ArchColumn title="Software system">
            {software.map((p) => (
              <ArchRow key={p.name} name={p.name} status={p.status} icon={p.icon} />
            ))}
          </ArchColumn>
        </div>
      </Section>
    </>
  );
}

function ArchColumn({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-card bg-paper p-6 md:p-8">
      <h3 className="text-2xl font-medium">{title}</h3>
      <ul className="mt-6 space-y-3">{children}</ul>
    </div>
  );
}

function ArchRow({ name, status, icon: Icon }: { name: string; status: "concept" | "planned" | "live"; icon?: typeof Database }) {
  return (
    <li className="flex items-center justify-between gap-4 rounded-xl border border-line bg-white/70 px-4 py-3">
      <span className="flex min-w-0 items-center gap-3 text-sm font-medium text-charcoal">
        {Icon ? <Icon className="size-4 shrink-0 text-forest" aria-hidden /> : <span className="size-2 shrink-0 rounded-full bg-forest-soft" aria-hidden />}
        {name}
      </span>
      <StatusTag status={status} />
    </li>
  );
}
