import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { HudLabel, PageHeader } from "@/components/hud";
import { SleepChart } from "@/components/sleep-chart";
import { getReport } from "@/lib/api";
import type { Mood, Report, Tone } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const toneText: Record<Tone, string> = {
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
  muted: "text-muted-foreground",
};

const toneBadge: Record<Tone, "hud" | "success" | "warning" | "destructive" | "muted"> = {
  primary: "hud",
  success: "success",
  warning: "warning",
  destructive: "destructive",
  muted: "muted",
};

const moodStyle: Record<Mood, string> = {
  pleasant: "bg-success/20 text-success",
  neutral: "bg-muted text-muted-foreground",
  unpleasant: "bg-warning/15 text-warning",
};

export default function ReportPage() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Suspense fallback={<ReportMessage title="Your week, explained" body="Loading your weekly report…" />}>
        <ReportContent />
      </Suspense>
    </div>
  );
}

async function ReportContent() {
  let report: Report;
  try {
    report = await getReport();
  } catch {
    return (
      <ReportMessage
        title="Report unavailable"
        body="Couldn't reach the backend. Start it with `python manage.py runserver` and reload."
      />
    );
  }
  return <ReportView report={report} />;
}

function ReportMessage({ title, body }: { title: string; body: string }) {
  return (
    <>
      <PageHeader eyebrow="Weekly report" title={title} />
      <p className="text-muted-foreground text-[15px]">{body}</p>
    </>
  );
}

function ReportView({ report }: { report: Report }) {
  const maxHours = Math.max(1, ...report.timeUse.map((t) => t.hours));
  const sleepDelta = report.stats.find((s) => s.label === "Avg sleep")?.delta;

  return (
    <>
      <PageHeader eyebrow={`Weekly report · ${report.label}`} title="Your week, explained" />

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {report.stats.map((s) => (
          <div key={s.label} className="bg-card flex flex-col gap-1.5 rounded-xl border p-4">
            <span className="text-muted-foreground text-[13px]">{s.label}</span>
            <span className="font-mono text-2xl">
              {s.value}
              {s.suffix && <span className="text-muted-foreground text-sm"> {s.suffix}</span>}
            </span>
            <span className={cn("font-mono text-xs", toneText[s.tone])}>{s.delta} vs last week</span>
          </div>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Sleep per night</CardTitle>
            {sleepDelta && (
              <CardAction>
                <span className="text-muted-foreground font-mono text-xs">avg {sleepDelta}</span>
              </CardAction>
            )}
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <SleepChart days={report.days} sleepThis={report.sleepThis} sleepLast={report.sleepLast} />
            <div className="flex flex-col gap-2">
              <HudLabel>Readiness and mood this week</HudLabel>
              <div className="grid grid-cols-7 gap-1.5">
                {report.days.map((d, i) => {
                  const mood = report.moodThis[i];
                  return (
                    <div key={d} className="flex flex-col items-center gap-1">
                      <span className="text-muted-foreground font-mono text-[10px]">{d.toUpperCase()}</span>
                      <span className="bg-muted w-full rounded-md py-1.5 text-center font-mono text-sm">
                        {report.readinessThis[i] ?? "–"}
                      </span>
                      <span
                        className={cn(
                          "w-full rounded-md py-1 text-center text-[10px]",
                          mood ? moodStyle[mood] : "bg-muted text-muted-foreground",
                        )}
                      >
                        {mood ?? "no log"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader>
              <CardTitle>Biggest changes</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {report.changes.map((c) => (
                <div key={c.title} className="bg-muted flex flex-col gap-1 rounded-lg p-3.5">
                  <span className="text-[15px] font-semibold">{c.title}</span>
                  <span className="text-muted-foreground text-[13px] leading-relaxed">{c.body}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Where your time went</CardTitle>
              <CardDescription>Hours from your calendar</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {report.timeUse.map((t) => (
                <div key={t.category} className="grid grid-cols-[64px_minmax(0,1fr)_76px] items-center gap-3 text-sm">
                  <span>{t.category}</span>
                  <div className="bg-muted h-2 rounded-full" role="img" aria-label={`${t.category}: ${t.hours} hours`}>
                    <div className="bg-chart-1 h-2 rounded-full" style={{ width: `${(t.hours / maxHours) * 100}%` }} />
                  </div>
                  <span className="text-right font-mono text-xs">
                    {t.hours}h <span className="text-muted-foreground">({t.delta})</span>
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Did my advice work?</CardTitle>
          <CardDescription>
            The agent checks suggestions you took against your data a week later. It shows what changed
            afterwards, not proof the suggestion caused it.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {report.followUps.length === 0 && (
            <p className="text-muted-foreground text-sm md:col-span-3">
              No suggestions to check yet. Add one from the Today or Week page and it shows up here.
            </p>
          )}
          {report.followUps.map((f) => (
            <div key={f.id} className="bg-muted flex flex-col gap-2 rounded-lg p-4">
              <Badge variant={toneBadge[f.tone]}>{f.result.toUpperCase()}</Badge>
              <span className="text-[15px] font-semibold">{f.suggestion}</span>
              <span className="text-muted-foreground font-mono text-xs">{f.detail}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </>
  );
}
