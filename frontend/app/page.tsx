import Link from "next/link";
import { RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CornerBrackets, DayStrip, HudLabel, ReadinessRing } from "@/components/hud";
import { AskBox } from "@/components/ask-box";
import { activeExperiment, brief, goals, today, type TimelineItem } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export default function BriefPage() {
  const { readiness } = brief;
  const exp = activeExperiment;
  const kept = exp.days.filter((d) => d === "kept").length;
  const missed = exp.days.filter((d) => d === "missed").length;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="hud-label text-primary">{brief.dateLabel}</span>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Good morning, {brief.greetingName}.
          </h1>
          <p className="text-muted-foreground text-[15px]">Here&apos;s your brief. Readable in under a minute.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Badge variant="warning">MOCK DATA</Badge>
          <Button variant="outline" size="lg">
            <RefreshCw /> Regenerate brief
          </Button>
          <Button asChild size="lg">
            <Link href="/ask">Ask agent</Link>
          </Button>
        </div>
      </header>

      <section className="grid gap-5 lg:grid-cols-3">
        <Card className="relative items-center gap-4 px-6">
          <CornerBrackets />
          <HudLabel className="self-start">Day readiness</HudLabel>
          <ReadinessRing
            value={readiness.score}
            secondary={(readiness.energyForecast / 5) * 100}
            label={`Readiness ${readiness.score} out of 100`}
          />
          <div className="grid w-full grid-cols-3 gap-2 text-center">
            <Metric value={readiness.sleep} label="sleep" />
            <Metric value={`${readiness.energyForecast}/5`} label="energy (pred.)" className="text-warning" />
            <Metric value={String(readiness.deadlines)} label="deadlines" />
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Daily brief</CardTitle>
            <CardAction>
              <span className="text-success font-mono text-[11px]">
                ✓ PASSED CRITIC · {brief.critic.toolCalls} TOOL CALLS
              </span>
            </CardAction>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {brief.sections.map((s) => (
              <div
                key={s.key}
                className={cn(
                  "flex flex-col gap-2 rounded-lg p-4",
                  s.highlight ? "border-warning/45 bg-warning/5 border" : "bg-muted",
                )}
              >
                <span className={cn("hud-label", s.highlight ? "text-warning" : "text-primary")}>{s.label}</span>
                <p className="text-[15px] leading-relaxed">
                  {s.body}{" "}
                  {s.evidence && (
                    <span className="text-muted-foreground font-mono text-xs">{s.evidence}</span>
                  )}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Goals · this week</CardTitle>
            <CardAction>
              <Button variant="link" size="sm" className="h-auto px-0">Edit</Button>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            {goals.map((g) => {
              const pct = Math.min(100, Math.round((g.current / g.target) * 100));
              return (
                <div key={g.id} className="flex flex-col gap-2">
                  <div className="flex justify-between text-sm">
                    <span>{g.title}</span>
                    <span className={cn("font-mono", g.onTrack ? "text-success" : "text-warning")}>
                      {g.current} / {g.target}
                    </span>
                  </div>
                  <Progress
                    value={pct}
                    aria-label={`${g.title}: ${pct}%`}
                    indicatorClassName={g.onTrack ? "bg-success" : "bg-warning"}
                  />
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Today</CardTitle>
            <CardAction>
              <Link href="/plan" className="text-primary text-sm hover:underline">Open week</Link>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {today.map((item) => (
              <TimelineRow key={item.time + item.title} item={item} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Running experiment</CardTitle>
            <CardAction>
              <Badge variant="hud">DAY {exp.day}/{exp.durationDays}</Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-4">
            <p className="text-[15px] leading-relaxed">{exp.shortHypothesis}</p>
            <DayStrip days={exp.days} label={`Adherence: ${kept} kept, ${missed} missed`} />
            <div className="text-muted-foreground flex justify-between font-mono text-xs">
              <span>kept {kept} · missed {missed}</span>
              <span>too early to call (n={exp.day})</span>
            </div>
            <Button asChild variant="outline" size="lg" className="mt-auto">
              <Link href="/learn">View experiment</Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <AskBox />
    </div>
  );
}

function Metric({ value, label, className }: { value: string; label: string; className?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className={cn("font-mono text-lg", className)}>{value}</span>
      <span className="text-muted-foreground text-xs">{label}</span>
    </div>
  );
}

function TimelineRow({ item }: { item: TimelineItem }) {
  return (
    <div className="flex items-stretch gap-3.5">
      <span
        className={cn(
          "w-12 shrink-0 pt-2.5 font-mono text-xs",
          item.kind === "deadline" ? "text-destructive" : "text-muted-foreground",
        )}
      >
        {item.time}
      </span>
      <div
        className={cn(
          "flex-1 rounded-lg px-3.5 py-2.5",
          item.kind === "suggested" && "border-primary/60 bg-primary/5 border border-dashed",
          (item.kind === "fixed" || item.kind === "goal") && "bg-muted",
          item.kind === "deadline" && "border-destructive/45 border",
        )}
      >
        <div className="text-sm font-semibold">{item.title}</div>
        <div className={cn("text-xs", item.kind === "suggested" ? "text-primary font-mono" : "text-muted-foreground")}>
          {item.meta}
        </div>
      </div>
    </div>
  );
}
