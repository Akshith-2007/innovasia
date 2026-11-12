/** Explanatory diagrams. They show concepts, not measured performance. */

export function WaterLoopDiagram({ className }: { className?: string }) {
  return (
    <figure className={className}>
      <svg viewBox="0 0 640 300" role="img" aria-labelledby="loop-title loop-desc" className="h-auto w-full">
        <title id="loop-title">Independent water circulation loop</title>
        <desc id="loop-desc">
          Water flows from a reservoir through a pump into an aluminium coil inside the storage chamber, then returns to
          the reservoir. A separate cooling source re-cools the reservoir water.
        </desc>
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L10 5 L0 10z" fill="#1f4d36" />
          </marker>
        </defs>
        {/* reservoir */}
        <rect x="20" y="150" width="130" height="110" rx="14" fill="#e3e9dd" stroke="#1f4d36" strokeWidth="1.5" />
        <rect x="20" y="195" width="130" height="65" rx="0" fill="#c9d5c1" opacity="0.7" />
        <text x="85" y="178" textAnchor="middle" fontSize="13" fontWeight="600" fill="#1c1f1d">Reservoir</text>
        {/* cooling source */}
        <rect x="20" y="40" width="130" height="60" rx="12" fill="#fff" stroke="#c8892b" strokeDasharray="5 4" strokeWidth="1.5" />
        <text x="85" y="66" textAnchor="middle" fontSize="12" fontWeight="600" fill="#7a5016">Separate</text>
        <text x="85" y="83" textAnchor="middle" fontSize="12" fontWeight="600" fill="#7a5016">cooling source</text>
        <path d="M85 100 V148" stroke="#c8892b" strokeWidth="1.5" strokeDasharray="4 4" markerEnd="url(#arr)" />
        {/* pump */}
        <circle cx="245" cy="205" r="30" fill="#fff" stroke="#1f4d36" strokeWidth="1.5" />
        <path d="M232 205 h26 M245 192 v26" stroke="#1f4d36" strokeWidth="1.5" />
        <text x="245" y="258" textAnchor="middle" fontSize="13" fontWeight="600" fill="#1c1f1d">Pump</text>
        {/* chamber with coil */}
        <rect x="350" y="40" width="270" height="220" rx="18" fill="#f6f3ec" stroke="#1f4d36" strokeWidth="1.5" />
        <text x="485" y="66" textAnchor="middle" fontSize="13" fontWeight="600" fill="#1c1f1d">Storage chamber</text>
        <path
          d="M380 205 h210 a12 12 0 0 0 0 -24 h-210 a12 12 0 0 1 0 -24 h210 a12 12 0 0 0 0 -24 h-210 a12 12 0 0 1 0 -24 h210"
          fill="none"
          stroke="#9aa3a0"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <text x="485" y="236" textAnchor="middle" fontSize="12" fill="#646a63">Aluminium coil</text>
        {/* flows */}
        <path d="M150 205 H213" stroke="#1f4d36" strokeWidth="2" markerEnd="url(#arr)" />
        <path d="M275 205 H372" stroke="#1f4d36" strokeWidth="2" markerEnd="url(#arr)" />
        <path d="M600 109 C 640 109, 640 285, 500 285 H 110 C 90 285, 85 275, 85 262" fill="none" stroke="#1f4d36" strokeWidth="2" markerEnd="url(#arr)" />
        <text x="330" y="280" textAnchor="middle" fontSize="12" fill="#646a63">Warmer water returns</text>
      </svg>
      <figcaption className="mt-3 text-sm text-muted">
        Water carries cooling; it does not create it. The reservoir must be re-cooled by a separate source.
      </figcaption>
    </figure>
  );
}

export function PcmDiagram({ className }: { className?: string }) {
  return (
    <figure className={className}>
      <svg viewBox="0 0 640 260" role="img" aria-labelledby="pcm-title pcm-desc" className="h-auto w-full">
        <title id="pcm-title">Phase-change material charging and discharging</title>
        <desc id="pcm-desc">
          Temperature against heat. While the PCM changes phase, temperature stays almost flat as latent heat is stored or
          released, creating a thermal buffer.
        </desc>
        <line x1="60" y1="210" x2="610" y2="210" stroke="#1c1f1d" strokeWidth="1.2" />
        <line x1="60" y1="210" x2="60" y2="20" stroke="#1c1f1d" strokeWidth="1.2" />
        <text x="335" y="245" textAnchor="middle" fontSize="12" fill="#646a63">Heat absorbed by the PCM →</text>
        <text x="22" y="120" textAnchor="middle" fontSize="12" fill="#646a63" transform="rotate(-90 22 120)">Temperature</text>
        <rect x="200" y="20" width="250" height="190" fill="#e3e9dd" />
        <text x="325" y="44" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1f4d36">Phase change: latent heat</text>
        <path d="M70 190 L200 125 L450 118 L600 40" fill="none" stroke="#1f4d36" strokeWidth="3" strokeLinejoin="round" />
        <text x="120" y="182" fontSize="12" fill="#1c1f1d">Solid</text>
        <text x="525" y="95" fontSize="12" fill="#1c1f1d">Liquid</text>
        <text x="325" y="150" textAnchor="middle" fontSize="12" fill="#646a63">Near-constant temperature</text>
        <text x="325" y="185" textAnchor="middle" fontSize="11" fill="#7a5016">Discharge: chamber heat melts the PCM</text>
        <text x="325" y="200" textAnchor="middle" fontSize="11" fill="#7a5016">Charge: cooling source re-freezes it</text>
      </svg>
      <figcaption className="mt-3 text-sm text-muted">
        Illustrative curve. Actual phase-change temperature and capacity depend on the chosen material.
      </figcaption>
    </figure>
  );
}
