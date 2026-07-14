import { bandHex } from "@/lib/utils";

const R = 80;
const CX = 100;
const CY = 100;
const ARC_LEN = Math.PI * R; // semicircle length

export function RiskGauge({ score, band }: { score: number; band: string }) {
  const color = bandHex(band);
  const offset = ARC_LEN * (1 - Math.max(0, Math.min(100, score)) / 100);
  return (
    <div className="relative flex flex-col items-center">
      <svg viewBox="0 0 200 120" className="w-full max-w-[260px]">
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          fill="none"
          stroke="hsl(var(--secondary))"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={ARC_LEN}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease-out, stroke 0.4s" }}
        />
        <text x={CX} y={CY - 18} textAnchor="middle" className="fill-foreground" style={{ fontSize: 34, fontWeight: 800 }}>
          {score}
        </text>
        <text x={CX} y={CY + 2} textAnchor="middle" className="fill-muted-foreground" style={{ fontSize: 10, letterSpacing: 1 }}>
          RISK SCORE
        </text>
      </svg>
      <div
        className="mt-1 rounded-full px-4 py-1 text-sm font-bold uppercase tracking-wider"
        style={{ color, backgroundColor: `${color}22` }}
      >
        {band}
      </div>
    </div>
  );
}
