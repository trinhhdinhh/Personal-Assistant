import { Suspense } from "react";
import Link from "next/link";
import { ArrowRight, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CornerBrackets, HudLabel, ReadinessRing } from "@/components/hud";
import { AskBox } from "@/components/ask-box";
import { SuggestionItem } from "@/components/suggestion";
import { getBrief, type Brief, type ScheduleItem } from "@/lib/api";
import { profile } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export default function TodayPage() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Suspense fallback={<Greeting label="TODAY" line="Loading your brief…" />}>
        <BriefContent />
      </Suspense>
      <AskBox />
    </div>
  );
}

async function BriefContent() {
  let brief: Brief;
  try {
    brief = await getBrief();
  } catch {
    return <Greeting label="TODAY" line="Couldn't reach the backend. Start it with `python manage.py runserver` and reload." />;
  }
  return <BriefView brief={brief} />;
}

function Greeting({ label, line }: { label: string; line: string }) {
  return (
    <header className="flex flex-col gap-1.5">
      <span className="hud-label text-primary">{label}</span>
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Good morning, {profile.name}.</h1>
      <p className="text-muted-foreground text-[15px]">{line}</p>
    </header>
  );
}

function shortDate(iso: string) {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function BriefView({ brief }: { brief: Brief }) {
  const count = brief.suggestions.length;
  const health = brief.health;

  return (
    <>
      <Greeting
        label={brief.dateLabel}
        line={count ? `${count} thing${count > 1 ? "s" : ""} for today, based on your data.` : "Nothing to change today."}
      />

      <section className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card className="relative items-center gap-4 px-6">
          <CornerBrackets />
          <div className="flex w-full items-baseline justify-between">
            <HudLabel>Readiness</HudLabel>
            {health && <span className="text-muted-foreground font-mono text-[10px]">AS OF {shortDate(health.asOf).toUpperCase()}</span>}
          </div>
          {health ? (
            <>
              <ReadinessRing score={health.readiness.score} max={health.readiness.max} level={health.readiness.level} />
              <div className="grid w-full grid-cols-3 gap-2 text-center">
                {health.vitals.map((v) => (
                  <div key={v.label} className="flex flex-col gap-0.5">
                    <span className="font-mono text-base">{v.value}</span>
                    <span className="text-muted-foreground text-xs">{v.label}</span>
                    <span className="text-muted-foreground font-mono text-[10px]">{v.note}</span>
                  </div>
                ))}
              </div>
              {health.mood && (
                <div className="bg-muted flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm">
                  <span className="text-muted-foreground">Latest mood</span>
                  <span>{health.mood}</span>
                </div>
              )}
            </>
          ) : (
            <p className="text-muted-foreground py-8 text-sm">No health data in the last three weeks.</p>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Suggestions for today</CardTitle>
            <CardAction>
              <span className="text-success font-mono text-[11px]">FROM YOUR DATA · {brief.toolCalls} TOOL CALLS</span>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {count ? (
              brief.suggestions.map((s) => <SuggestionItem key={s.id} suggestion={s} />)
            ) : (
              <p className="text-muted-foreground text-sm">Your day looks fine as planned.</p>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Today&apos;s schedule</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2.5">
            {brief.schedule.length ? (
              brief.schedule.map((item) => <ScheduleRow key={`${item.start}-${item.title}`} item={item} />)
            ) : (
              <p className="text-muted-foreground text-sm">Nothing booked today.</p>
            )}
          </CardContent>
        </Card>

        <Card className={cn(brief.headsUp && "border-warning/45")}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {brief.headsUp && <TriangleAlert className="text-warning size-5" aria-hidden="true" />} Heads up this week
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-4">
            <p className="text-[15px] leading-relaxed">
              {brief.headsUp?.text ?? "No rough days in the forecast for the rest of the week."}
            </p>
            <Button asChild variant="outline" size="lg" className="mt-auto w-fit">
              <Link href="/week">
                See week ahead <ArrowRight />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </>
  );
}

function ScheduleRow({ item }: { item: ScheduleItem }) {
  return (
    <div className="flex items-stretch gap-3.5">
      <span className="text-muted-foreground w-12 shrink-0 pt-2 font-mono text-xs">{item.start}</span>
      <div
        className={cn(
          "flex flex-1 items-center justify-between gap-2 rounded-lg px-3.5 py-2",
          item.kind === "event" && "bg-muted",
          item.kind === "suggested" && "border-primary/60 bg-primary/5 text-primary border border-dashed",
        )}
      >
        <span className="text-sm font-medium">{item.title}</span>
        <span className="text-muted-foreground font-mono text-[11px]">until {item.end}</span>
      </div>
    </div>
  );
}
