import { cn } from "@/lib/utils";

/** The concentric-ring logo mark. */
export function CoreMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 36 36" aria-hidden="true" className={cn("text-primary shrink-0", className)}>
      <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="74 26" />
      <circle cx="18" cy="18" r="10" fill="none" stroke="currentColor" strokeOpacity="0.45" strokeWidth="1" />
      <circle cx="18" cy="18" r="4" fill="currentColor" />
    </svg>
  );
}

/** Cyan corner brackets for "targeted" HUD panels. Parent must be `relative`. */
export function CornerBrackets({ all = false }: { all?: boolean }) {
  const base = "border-primary pointer-events-none absolute size-3.5";
  return (
    <>
      <span aria-hidden="true" className={cn(base, "top-2.5 left-2.5 border-t-2 border-l-2")} />
      {all && <span aria-hidden="true" className={cn(base, "top-2.5 right-2.5 border-t-2 border-r-2")} />}
      {all && <span aria-hidden="true" className={cn(base, "bottom-2.5 left-2.5 border-b-2 border-l-2")} />}
      <span aria-hidden="true" className={cn(base, "right-2.5 bottom-2.5 border-r-2 border-b-2")} />
    </>
  );
}

/** Mono, letter-spaced section label. */
export function HudLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={cn("hud-label text-muted-foreground", className)}>{children}</span>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-1.5">
        <span className="hud-label text-primary">{eyebrow}</span>
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground text-[15px]">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </header>
  );
}

/** Big ring gauge (0–100) with a thinner secondary arc. */
export function ReadinessRing({
  value,
  secondary,
  label,
}: {
  value: number;
  secondary: number;
  label: string;
}) {
  const r1 = 84;
  const r2 = 66;
  const c1 = 2 * Math.PI * r1;
  const c2 = 2 * Math.PI * r2;
  return (
    <svg viewBox="0 0 220 220" role="img" aria-label={label} className="w-full max-w-[220px]">
      <circle cx="110" cy="110" r="100" fill="none" stroke="var(--border)" strokeWidth="1" />
      <circle cx="110" cy="110" r="100" fill="none" stroke="var(--primary)" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="2 8" />
      <circle cx="110" cy="110" r={r1} fill="none" stroke="var(--muted)" strokeWidth="10" />
      <circle
        cx="110" cy="110" r={r1} fill="none" stroke="var(--primary)" strokeWidth="10" strokeLinecap="round"
        strokeDasharray={`${(value / 100) * c1} ${c1}`} transform="rotate(-90 110 110)"
      />
      <circle
        cx="110" cy="110" r={r2} fill="none" stroke="var(--warning)" strokeOpacity="0.7" strokeWidth="2"
        strokeDasharray={`${(secondary / 100) * c2} ${c2}`} transform="rotate(-90 110 110)"
      />
      <text x="110" y="114" textAnchor="middle" fill="var(--foreground)" fontSize="52" fontWeight="600" fontFamily="var(--font-sans)">
        {value}
      </text>
      <text x="110" y="142" textAnchor="middle" fill="var(--muted-foreground)" fontSize="11" letterSpacing="2" fontFamily="var(--font-mono)">
        OF 100
      </text>
    </svg>
  );
}

/** Row of daily status cells (kept / missed / pending). */
export function DayStrip({
  days,
  label,
  tall = false,
}: {
  days: ("kept" | "missed" | "pending" | "today")[];
  label: string;
  tall?: boolean;
}) {
  return (
    <div
      role="img"
      aria-label={label}
      className="grid gap-1"
      style={{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }}
    >
      {days.map((d, i) => (
        <span
          key={i}
          className={cn(
            "rounded-[5px]",
            tall ? "h-8" : "h-5",
            d === "kept" && "bg-success",
            d === "missed" && "bg-destructive",
            d === "pending" && "bg-muted",
            d === "today" && "bg-muted border-primary border",
          )}
        />
      ))}
    </div>
  );
}
