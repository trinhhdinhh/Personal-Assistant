const W = 560;
const H = 240;
const PAD = { left: 36, right: 8, top: 12, bottom: 28 };
const Y_MAX = 10;
const BAR = 14;
const GAP = 2;

const y = (h: number) => PAD.top + (1 - Math.min(h, Y_MAX) / Y_MAX) * (H - PAD.top - PAD.bottom);
const baseline = y(0);

/** Bar with a 4px rounded top, square at the baseline. */
function bar(x: number, value: number) {
  const top = y(value);
  const r = Math.min(4, (baseline - top) / 2);
  return `M${x},${baseline} V${top + r} Q${x},${top} ${x + r},${top} H${x + BAR - r} Q${x + BAR},${top} ${x + BAR},${top + r} V${baseline} Z`;
}

const fmt = (h: number) => {
  const minutes = Math.round(h * 60);
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
};

type Props = {
  days: string[];
  sleepThis: (number | null)[];
  sleepLast: (number | null)[];
};

/** Hours of sleep per night, this week vs last week (one axis, grouped bars). Nights without data get no bar. */
export function SleepChart({ days, sleepThis, sleepLast }: Props) {
  const slot = (W - PAD.left - PAD.right) / days.length;

  return (
    <div className="flex flex-col gap-3">
      <div className="text-muted-foreground flex gap-4 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="bg-chart-1 size-2.5 rounded-sm" aria-hidden="true" /> This week
        </span>
        <span className="flex items-center gap-1.5">
          <span className="bg-chart-2 size-2.5 rounded-sm" aria-hidden="true" /> Last week
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Sleep per night this week versus last week" className="h-auto w-full">
        <g stroke="var(--border)">
          {[2, 4, 6, 8, 10].map((v) => (
            <line key={v} x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} strokeDasharray="2 6" />
          ))}
          <line x1={PAD.left} x2={W - PAD.right} y1={baseline} y2={baseline} />
        </g>
        <g fill="var(--muted-foreground)" fontFamily="var(--font-mono)" fontSize="11">
          {[0, 5, 10].map((v) => (
            <text key={v} x={PAD.left - 8} y={y(v) + 4} textAnchor="end">{v}h</text>
          ))}
          {days.map((d, i) => (
            <text key={d} x={PAD.left + slot * i + slot / 2} y={H - 8} textAnchor="middle">{d}</text>
          ))}
        </g>
        {days.map((d, i) => {
          const x0 = PAD.left + slot * i + slot / 2 - BAR - GAP / 2;
          const thisNight = sleepThis[i];
          const lastNight = sleepLast[i];
          return (
            <g key={d}>
              {thisNight != null && (
                <path d={bar(x0, thisNight)} fill="var(--chart-1)">
                  <title>{`${d} this week: ${fmt(thisNight)}`}</title>
                </path>
              )}
              {lastNight != null && (
                <path d={bar(x0 + BAR + GAP, lastNight)} fill="var(--chart-2)">
                  <title>{`${d} last week: ${fmt(lastNight)}`}</title>
                </path>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
