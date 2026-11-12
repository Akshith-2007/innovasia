import { PageHero, Reveal, Section } from "@/components/sections/primitives";

const blocks = [
  {
    label: "Vision",
    title: "Every harvest reaches market at its full value.",
    body: "We imagine a cold chain that begins at the farm gate, where preserving produce is affordable, reliable and paired with the information needed to sell it well.",
  },
  {
    label: "Mission",
    title: "Combine dependable cooling with trustworthy market intelligence.",
    body: "We are developing thermal-storage cooling concepts and an analytics platform built strictly on official government data, so that storage and selling decisions reinforce each other.",
  },
  {
    label: "Problem",
    title: "Storage, temperature and information fail at the same moment.",
    body: "Perishables lose quality quickly without stable cooling. Cold storage is often out of reach for small producers, and the price information that could guide timing is fragmented across official sources.",
  },
  {
    label: "Solution",
    title: "A link between preservation and decision-making.",
    body: "Phase-change thermal storage and an independent water loop aim to hold produce in a stable environment. A data platform turns AGMARKNET mandi prices into history, comparisons and evaluated forecasts.",
  },
  {
    label: "Product philosophy",
    title: "Honest by design.",
    body: "We label concepts as concepts. Every price shows its source and observation date. Forecasts come from a model trained and evaluated on real observations, and when the data is not good enough, we say so.",
  },
  {
    label: "Long-term direction",
    title: "From demonstration to the field.",
    body: "Next come field prototypes with instrumented monitoring, deeper historical market coverage and, later, Telugu-first voice access to market information for farmers.",
  },
];

export default function AboutPage() {
  return (
    <>
      <title>About — Kisan Cold Link</title>
      <PageHero
        eyebrow="About"
        title="Building the missing link between the field and the market."
        lede="Kisan Cold Link is an AgriTech initiative combining intelligent agricultural cooling with data-driven market intelligence."
      />
      <Section>
        <div className="divide-y divide-line">
          {blocks.map((b, i) => (
            <Reveal key={b.label} delay={i * 0.03}>
              <article className="grid gap-4 py-12 md:grid-cols-[14rem_1fr] md:gap-12 md:py-16">
                <p className="eyebrow pt-2">{b.label}</p>
                <div className="max-w-3xl">
                  <h2 className="text-3xl leading-tight font-medium md:text-4xl">{b.title}</h2>
                  <p className="mt-5 text-lg leading-relaxed text-muted">{b.body}</p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </Section>
    </>
  );
}
