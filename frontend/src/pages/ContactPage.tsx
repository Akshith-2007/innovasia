import { ArrowUpRight, Handshake, Mail, MonitorPlay } from "lucide-react";

import { PageHero, Section } from "@/components/sections/primitives";
import { site } from "@/lib/site";

function mailto(address: string, subject: string) {
  return `mailto:${address}?subject=${encodeURIComponent(subject)}`;
}

export default function ContactPage() {
  const channels = [
    { icon: Mail, title: "General enquiries", body: "Questions about the product, data or technology.", address: site.contactEmail, subject: "Kisan Cold Link enquiry" },
    { icon: Handshake, title: "Partnerships", body: "Institutions, cold-storage operators, government bodies and technology partners.", address: site.partnershipEmail, subject: "Partnership with Kisan Cold Link" },
    { icon: MonitorPlay, title: "Request a demo", body: "A walkthrough of the market intelligence platform and the cooling concept.", address: site.contactEmail, subject: "Demo request: Kisan Cold Link" },
  ];
  return (
    <>
      <title>Contact — Kisan Cold Link</title>
      <PageHero eyebrow="Contact" title="Let's talk about the cold chain." lede="We are looking for partners, pilots and people who care about what happens to produce after harvest." />
      <Section>
        <ul className="grid gap-6 md:grid-cols-3">
          {channels.map(({ icon: Icon, title, body, address, subject }) => (
            <li key={title} className="flex flex-col rounded-card border border-line bg-white p-7">
              <Icon className="size-6 text-forest" aria-hidden />
              <h2 className="mt-8 text-2xl font-medium">{title}</h2>
              <p className="mt-2 flex-1 text-muted">{body}</p>
              {address ? (
                <a href={mailto(address, subject)} className="mt-6 inline-flex items-center gap-1 font-semibold text-forest hover:underline">
                  {address} <ArrowUpRight className="size-4" />
                </a>
              ) : (
                <p className="mt-6 text-sm text-muted italic">Email address being set up.</p>
              )}
            </li>
          ))}
        </ul>
        {site.social.length ? (
          <div className="mt-12 flex flex-wrap items-center gap-3">
            <span className="eyebrow mr-2">Follow</span>
            {site.social.map((s) => (
              <a key={s.label} href={s.href} target="_blank" rel="noreferrer" className="rounded-full border border-line px-4 py-2 text-sm font-medium hover:border-forest hover:text-forest">
                {s.label}
              </a>
            ))}
          </div>
        ) : null}
      </Section>
    </>
  );
}
