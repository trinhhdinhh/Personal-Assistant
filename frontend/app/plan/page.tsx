import { CalendarPlus, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HudLabel, PageHeader } from "@/components/hud";
import { focusWindows, toPlace, week, type BlockKind } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const HOUR_PX = 40;

const blockStyle: Record<BlockKind, string> = {
  class: "bg-chart-4/60",
  work: "bg-[#2a2f45]",
  study: "bg-primary/15 border-l-[3px] border-primary",
  gym: "bg-success/20",
  social: "bg-warning/15 text-warning",
  suggested: "bg-primary/10 border border-dashed border-primary text-primary",
  skipped: "bg-destructive/10 border border-dashed border-destructive/60 text-destructive",
};

export default function PlanPage() {
  const hours = week.dayEnd - week.dayStart;
  const suggestedCount = week.days.flatMap((d) => d.blocks).filter((b) => b.kind === "suggested").length;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <PageHeader
        eyebrow={`Plan · ${week.label}`}
        title="This week"
        actions={
          <>
            {week.feasibility.feasible && (
              <Badge variant="success" className="h-8">
                ✓ FEASIBLE · {week.feasibility.solver.toUpperCase()} {week.feasibility.seconds}s
              </Badge>
            )}
            <Button variant="outline" size="lg">
              <RefreshCw /> Re-plan
            </Button>
            <Button size="lg">
              <CalendarPlus /> Send {suggestedCount} blocks to calendar
            </Button>
          </>
        }
      />

      <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
        <Card className="min-w-0 flex-1 px-4">
          <div className="overflow-x-auto">
            <div className="grid min-w-[720px] gap-1.5" style={{ gridTemplateColumns: "44px repeat(7, minmax(0, 1fr))" }}>
              <span />
              {week.days.map((d, i) => (
                <span
                  key={d.label}
                  className={cn(
                    "pb-1.5 text-center font-mono text-[11px]",
                    i === week.todayIndex ? "text-primary border-primary border-b-2" : "text-muted-foreground",
                  )}
                >
                  {d.label}
                </span>
              ))}

              <div className="text-muted-foreground relative font-mono text-[10px]" style={{ height: hours * HOUR_PX }}>
                {Array.from({ length: hours / 2 + 1 }, (_, i) => week.dayStart + i * 2).map((h) => (
                  <span key={h} className="absolute" style={{ top: Math.min((h - week.dayStart) * HOUR_PX, hours * HOUR_PX - 12) }}>
                    {String(h).padStart(2, "0")}
                  </span>
                ))}
              </div>

              {week.days.map((d, i) => (
                <div
                  key={d.label}
                  className={cn(
                    "relative rounded-md",
                    i === week.todayIndex ? "outline-primary/30 bg-[#0b1722] outline" : "bg-[#09111a]",
                  )}
                  style={{ height: hours * HOUR_PX }}
                >
                  {d.blocks.map((b) => (
                    <div
                      key={b.title + b.start}
                      className={cn("absolute inset-x-[3px] overflow-hidden rounded-md p-1.5 text-[11px]", blockStyle[b.kind])}
                      style={{
                        top: (b.start - week.dayStart) * HOUR_PX,
                        height: (b.end - b.start) * HOUR_PX,
                      }}
                    >
                      {b.title}
                    </div>
                  ))}
                  {d.deadlineAt && (
                    <div
                      className="bg-destructive absolute inset-x-0 h-0.5"
                      style={{ top: Math.min((d.deadlineAt - week.dayStart) * HOUR_PX, hours * HOUR_PX - 2) }}
                      aria-label="Deadline"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="text-muted-foreground flex flex-wrap gap-4 text-xs">
            <LegendItem className="bg-chart-4/60" label="Class" />
            <LegendItem className="bg-[#2a2f45]" label="Work" />
            <LegendItem className="border-primary border border-dashed" label="Suggested by agent" />
            <LegendItem className="bg-success/40" label="Gym" />
            <span className="flex items-center gap-1.5">
              <span className="bg-destructive h-0.5 w-3" aria-hidden="true" /> Deadline
            </span>
          </div>
        </Card>

        <aside className="flex flex-col gap-4 xl:w-80">
          <Card className="gap-3 py-5">
            <CardHeader className="px-5">
              <CardTitle className="text-base">To place</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2.5 px-5">
              {toPlace.map((t) => (
                <div key={t.title} className="bg-muted flex justify-between gap-2.5 rounded-lg p-3 text-sm">
                  <span>{t.title}</span>
                  <span className="text-muted-foreground font-mono text-xs">
                    {t.estimate}
                    {t.adjusted && (
                      <>
                        {" → "}
                        <span className="text-warning">{t.adjusted}</span>
                      </>
                    )}
                  </span>
                </div>
              ))}
              <p className="text-muted-foreground text-xs">Estimates adjusted from your timed sessions.</p>
            </CardContent>
          </Card>

          <Card className="gap-3 py-5">
            <CardHeader className="px-5">
              <CardTitle className="text-base">Your focus windows</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2.5 px-5">
              <div className="grid grid-cols-8 gap-[3px]" role="img" aria-label="Focus is highest 9 to 11am, lowest after 2pm">
                {focusWindows.map((v, i) => (
                  <span key={i} className="bg-primary h-10 rounded-[3px]" style={{ opacity: 0.15 + v * 0.85 }} />
                ))}
              </div>
              <div className="text-muted-foreground flex justify-between font-mono text-[10px]">
                <span>8a</span><span>12p</span><span>4p</span><span>8p</span>
              </div>
              <p className="text-[13px]">
                Best: <strong>9:30–11:30</strong>. Weakest: right after class.
              </p>
            </CardContent>
          </Card>

          <div className="border-warning/45 bg-warning/5 flex flex-col gap-2 rounded-xl border p-5">
            <HudLabel className="text-warning">Conflict resolved</HudLabel>
            <p className="text-sm leading-relaxed">
              Moved Tuesday&apos;s skipped study block to Thursday morning so the report finishes 24h early.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function LegendItem({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("size-3 rounded-[3px]", className)} aria-hidden="true" />
      {label}
    </span>
  );
}
