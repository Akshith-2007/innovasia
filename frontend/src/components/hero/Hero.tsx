import { ArrowRight } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

/** Field furrows converging on a horizon, with slow-drifting thermal contours. Pure SVG, no stock imagery. */
function FieldScape() {
  const reduce = useReducedMotion();
  const furrows = Array.from({ length: 22 }, (_, i) => i);
  return (
    <svg aria-hidden className="absolute inset-0 h-full w-full" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="sky" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#0d2418" />
          <stop offset="0.55" stopColor="#163a27" />
          <stop offset="1" stopColor="#1f4d36" />
        </linearGradient>
        <radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#e0b062" stopOpacity="0.55" />
          <stop offset="1" stopColor="#e0b062" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="soil" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#24563c" />
          <stop offset="1" stopColor="#12301f" />
        </linearGradient>
      </defs>
      <rect width="1440" height="900" fill="url(#sky)" />
      <circle cx="1060" cy="520" r="360" fill="url(#sun)" />
      <circle cx="1060" cy="520" r="74" fill="#e0b062" opacity="0.18" />
      {/* thermal contours */}
      <g fill="none" stroke="#c9d5c1" strokeOpacity="0.09" strokeWidth="1.2">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <motion.path
            key={i}
            d={`M-100 ${180 + i * 60} C 300 ${120 + i * 60}, 700 ${260 + i * 60}, 1540 ${170 + i * 60}`}
            animate={reduce ? undefined : { x: [0, 40, 0] }}
            transition={{ duration: 18 + i * 3, repeat: Infinity, ease: "easeInOut" }}
          />
        ))}
      </g>
      {/* horizon + field */}
      <path d="M0 560 L1440 540 L1440 900 L0 900Z" fill="url(#soil)" />
      <g stroke="#c9d5c1" strokeOpacity="0.16" strokeWidth="1">
        {furrows.map((i) => {
          const x = -400 + i * 105;
          return <line key={i} x1={720 + (x - 720) * 0.04} y1={552} x2={x} y2={900} />;
        })}
      </g>
      <g stroke="#e0b062" strokeOpacity="0.12" strokeWidth="1">
        {[600, 650, 715, 800].map((y) => (
          <line key={y} x1="0" x2="1440" y1={y} y2={y - 14} />
        ))}
      </g>
    </svg>
  );
}

export function Hero() {
  return (
    <section className="relative isolate flex min-h-[92svh] items-end overflow-hidden bg-forest-deep text-paper">
      <FieldScape />
      <div className="absolute inset-0 bg-gradient-to-t from-forest-deep via-forest-deep/30 to-transparent" aria-hidden />
      <div className="container-site relative pt-32 pb-16 md:pb-24">
        <motion.p
          className="eyebrow text-amber-soft!"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          Agricultural cold storage · Market intelligence
        </motion.p>
        <motion.h1
          className="mt-6 max-w-5xl text-[2.75rem] leading-[0.98] font-medium text-paper! text-balance sm:text-6xl md:text-7xl lg:text-[6.25rem]"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        >
          Preserving Produce.
          <br />
          <span className="italic text-sage">Powering Possibilities.</span>
        </motion.h1>
        <motion.div
          className="mt-8 flex flex-col gap-10 md:flex-row md:items-end md:justify-between"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        >
          <p className="max-w-xl text-lg leading-relaxed text-paper/80 text-pretty">
            Reimagining agricultural cold storage through intelligent thermal management, agricultural insights and
            accessible technology.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild variant="light" size="lg">
              <Link to="/technology">
                Explore Our Technology <ArrowRight />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="text-paper">
              <Link to="/market-intelligence">Explore Market Intelligence</Link>
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
