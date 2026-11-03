import { sleepFocus } from "@/lib/mock-data";

const W = 520;
const H = 280;
const PAD = { left: 44, right: 10, top: 20, bottom: 40 };
const X_MIN = 4;
const X_MAX = 9;
const Y_MIN = 1;
const Y_MAX = 5;

const x = (hours: number) => PAD.left + ((hours - X_MIN) / (X_MAX - X_MIN)) * (W - PAD.left - PAD.right);
const y = (focus: number) => H - PAD.bottom - ((focus - Y_MIN) / (Y_MAX - Y_MIN)) * (H - PAD.top - PAD.bottom);

/** Least-squares fit, so the trend line matches the plotted points. */
function fit(points: { sleep: number; focus: number }[]) {
  const n = points.length;
  const mx = points.reduce((s, p) => s + p.sleep, 0) / n;
  const my = points.reduce((s, p) => s + p.focus, 0) / n;
  const num = points.reduce((s, p) => s + (p.sleep - mx) * (p.focus - my), 0);
  const den = points.reduce((s, p) => s + (p.sleep - mx) ** 2, 0);
  const slope = num / den;
  return (h: number) => my + slope * (h - mx);
}

export function SleepFocusScatter() {
  const line = fit(sleepFocus);
  const x1 = 4.3;
  const x2 = 9;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Scatter plot: more sleep generally pairs with higher next-day focus"
      className="h-auto w-full"
    >
      <g stroke="var(--border)">
        <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={H - PAD.bottom} />
        <line x1={PAD.left} y1={H - PAD.bottom} x2={W - PAD.right} y2={H - PAD.bottom} />
        {[2, 3, 4].map((v) => (
          <line key={v} x1={PAD.left} y1={y(v)} x2={W - PAD.right} y2={y(v)} strokeDasharray="2 6" />
        ))}
      </g>

      <rect x={x(4)} y={PAD.top} width={x(6) - x(4)} height={H - PAD.top - PAD.bottom} fill="var(--warning)" fillOpacity="0.06" />
      <text x={x(4) + 8} y={PAD.top + 16} fill="var(--warning)" fontFamily="var(--font-mono)" fontSize="10">
        &lt; 6h zone
      </text>

      <g fill="var(--primary)" fillOpacity="0.75">
        {sleepFocus.map((p, i) => (
          <circle key={i} cx={x(p.sleep)} cy={y(p.focus)} r="4" />
        ))}
      </g>

      <line
        x1={x(x1)} y1={y(line(x1))} x2={x(x2)} y2={y(line(x2))}
        stroke="var(--primary)" strokeWidth="1.5" strokeDasharray="6 5"
      />

      <g fill="var(--muted-foreground)" fontFamily="var(--font-mono)" fontSize="11">
        {[1, 3, 5].map((v) => (
          <text key={v} x={PAD.left - 6} y={y(v) + 4} textAnchor="end">{v}</text>
        ))}
        {[4, 5, 6, 7, 8, 9].map((h) => (
          <text key={h} x={x(h)} y={H - PAD.bottom + 20} textAnchor="middle">{h}h</text>
        ))}
        <text x={W - PAD.right} y={H - 4} textAnchor="end">sleep</text>
        <text x={6} y={PAD.top - 6}>focus</text>
      </g>
    </svg>
  );
}
