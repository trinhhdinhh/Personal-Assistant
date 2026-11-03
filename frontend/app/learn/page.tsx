import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CornerBrackets, DayStrip, HudLabel, PageHeader } from "@/components/hud";
import { activeExperiment, completedExperiments, proposedExperiments, type Tone } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const badgeFor: Record<Tone, "success" | "warning" | "muted" | "hud" | "destructive"> = {
  success: "success",
  warning: "warning",
  muted: "muted",
  primary: "hud",
  destructive: "destructive",
};

export default function LearnPage() {
  const exp = activeExperiment;
  const lift = exp.interventionPct - exp.baselinePct;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <PageHeader
        eyebrow="Learn · n-of-1 experiments"
        title="What actually works for you"
        actions={
          <Button size="lg">
            <Plus /> New experiment
          </Button>
        }
      />

      <section className="bg-card border-primary/40 relative flex flex-col gap-7 rounded-xl border p-7 lg:flex-row">
        <CornerBrackets all />
        <div className="flex min-w-0 flex-[2] flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant="hud">● RUNNING · DAY {exp.day}/{exp.durationDays}</Badge>
            <span className="text-muted-foreground font-mono text-[11px]">{exp.startedLabel}</span>
          </div>
          <h2 className="text-2xl leading-snug font-semibold">{exp.hypothesis}</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Intervention" value={exp.intervention} />
            <Field label="Metric" value={exp.metric} />
            <Field label="Tracked by" value={exp.trackedBy} />
          </div>
          <div className="flex flex-col gap-2">
            <HudLabel>Daily adherence</HudLabel>
            <DayStrip
              tall
              days={exp.days}
              label={`Kept ${exp.days.filter((d) => d === "kept").length} nights, missed ${exp.days.filter((d) => d === "missed").length}`}
            />
            <div className="text-muted-foreground flex gap-4 text-xs">
              <span className="flex items-center gap-1.5"><span className="bg-success size-2.5 rounded-sm" />kept</span>
              <span className="flex items-center gap-1.5"><span className="bg-destructive size-2.5 rounded-sm" />missed</span>
              <span className="flex items-center gap-1.5"><span className="border-primary size-2.5 rounded-sm border" />tonight</span>
            </div>
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-3.5 rounded-xl border bg-[#08101a] p-5 lg:max-w-xs">
          <HudLabel>Interim result</HudLabel>
          <ResultBar label="Baseline (30d)" pct={exp.baselinePct} indicator="bg-chart-4" />
          <ResultBar label="Kept nights" pct={exp.interventionPct} highlight />
          <div className="font-mono text-3xl">
            {lift > 0 ? "+" : ""}
            {lift} <span className="text-muted-foreground text-sm">pts</span>
          </div>
          <p className="text-warning text-[13px] leading-relaxed">
            Not significant yet (p = {exp.pValue}, n = {exp.day}). Final call on day {exp.durationDays}.
          </p>
          <Button variant="outline" size="lg" className="text-muted-foreground mt-auto bg-transparent">
            End early
          </Button>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Completed</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {completedExperiments.map((c) => (
              <div key={c.id} className="bg-muted flex flex-col gap-2 rounded-lg p-3.5">
                <div className="flex items-center justify-between gap-2.5">
                  <span className="text-[15px] font-semibold">{c.title}</span>
                  <Badge variant={badgeFor[c.tone]}>{c.result}</Badge>
                </div>
                <span className="text-muted-foreground text-[13px]">{c.detail}</span>
                <span className={cn("font-mono text-[11px]", c.tone === "muted" ? "text-muted-foreground" : "text-primary")}>
                  → {c.learned}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Proposed next</CardTitle>
            <CardAction>
              <span className="text-muted-foreground font-mono text-[11px]">from Know</span>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {proposedExperiments.map((p) => (
              <div key={p.id} className="border-primary/50 flex flex-col gap-2.5 rounded-lg border border-dashed p-4">
                <span className="text-[15px] font-semibold">{p.title}</span>
                <span className="text-muted-foreground text-[13px] leading-relaxed">Why: {p.why}</span>
                <div className="flex gap-2">
                  <Button>Start after current</Button>
                  <Button variant="outline">Dismiss</Button>
                </div>
              </div>
            ))}
            <p className="text-muted-foreground text-xs">One experiment at a time keeps results clean.</p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted flex flex-col gap-1 rounded-lg p-3">
      <span className="text-muted-foreground text-xs">{label}</span>
      <span className="text-sm">{value}</span>
    </div>
  );
}

function ResultBar({
  label,
  pct,
  indicator,
  highlight = false,
}: {
  label: string;
  pct: number;
  indicator?: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-[13px]">
        <span>{label}</span>
        <span className={cn("font-mono", highlight && "text-primary")}>{pct}%</span>
      </div>
      <Progress value={pct} aria-label={`${label}: ${pct}%`} className="h-2.5" indicatorClassName={indicator} />
    </div>
  );
}
