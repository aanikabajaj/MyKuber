import { bandHex } from "@/lib/utils";

interface MapPoint {
  latitude: number;
  longitude: number;
  city?: string;
  country?: string;
  risk_band: string;
  count: number;
}

const W = 720;
const H = 360;

function project(lat: number, lon: number) {
  return {
    x: ((lon + 180) / 360) * W,
    y: ((90 - lat) / 180) * H,
  };
}

// Coarse continent outlines (equirectangular) — stylised, for visual context.
const CONTINENTS: [number, number][][] = [
  // North America
  [[70, -160], [72, -80], [48, -55], [25, -80], [15, -95], [30, -118], [55, -130], [70, -160]],
  // South America
  [[10, -75], [5, -50], [-20, -40], [-40, -63], [-52, -70], [-20, -80], [0, -80], [10, -75]],
  // Europe
  [[70, -10], [70, 40], [45, 45], [36, 15], [43, -10], [60, -8], [70, -10]],
  // Africa
  [[35, -10], [32, 32], [10, 45], [-15, 40], [-35, 20], [-33, 15], [5, -12], [35, -10]],
  // Asia
  [[72, 45], [75, 140], [55, 145], [30, 122], [8, 100], [20, 60], [45, 48], [72, 45]],
  // Australia
  [[-12, 132], [-15, 145], [-38, 148], [-35, 118], [-20, 114], [-12, 132]],
];

export function WorldMap({ points }: { points: MapPoint[] }) {
  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="min-w-[640px] w-full rounded-lg bg-[hsl(224_44%_4%)]">
        {/* graticule */}
        {Array.from({ length: 13 }).map((_, i) => (
          <line key={`v${i}`} x1={(i * W) / 12} y1={0} x2={(i * W) / 12} y2={H} stroke="hsl(var(--border) / 0.35)" strokeWidth="0.5" />
        ))}
        {Array.from({ length: 7 }).map((_, i) => (
          <line key={`h${i}`} x1={0} y1={(i * H) / 6} x2={W} y2={(i * H) / 6} stroke="hsl(var(--border) / 0.35)" strokeWidth="0.5" />
        ))}
        {/* continents */}
        {CONTINENTS.map((poly, i) => (
          <polygon
            key={i}
            points={poly.map(([la, lo]) => { const p = project(la, lo); return `${p.x},${p.y}`; }).join(" ")}
            fill="hsl(var(--primary) / 0.08)"
            stroke="hsl(var(--primary) / 0.25)"
            strokeWidth="0.8"
          />
        ))}
        {/* login points */}
        {points.map((pt, i) => {
          const { x, y } = project(pt.latitude, pt.longitude);
          const color = bandHex(pt.risk_band);
          const r = Math.min(10, 4 + pt.count);
          return (
            <g key={i}>
              <circle cx={x} cy={y} r={r + 4} fill={color} opacity="0.15">
                <animate attributeName="r" values={`${r};${r + 8};${r}`} dur="2.5s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.25;0;0.25" dur="2.5s" repeatCount="indefinite" />
              </circle>
              <circle cx={x} cy={y} r={r} fill={color} opacity="0.9">
                <title>{`${pt.city || "?"}, ${pt.country || "?"} — ${pt.risk_band} (${pt.count})`}</title>
              </circle>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
