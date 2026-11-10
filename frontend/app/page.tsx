import Link from "next/link";
import { ArrowRight, TriangleAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CornerBrackets, HudLabel, ReadinessRing } from "@/components/hud";
import { AskBox } from "@/components/ask-box";
import { SuggestionItem } from "@/components/suggestion";
import { schedule, suggestionsToday, today, type ScheduleItem } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export default function TodayPage() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="hud-label text-primary">{today.dateLabel}</span>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Good morning, {today.name}.</h1>
          <p className="text-muted-foreground text-[15px]">Three things for today, based on your data.</p>
        </div>
        <Badge variant="warning">MOCK DATA</Badge>
      </header>

      <section className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card className="relative items-center gap-4 px-6">
          <CornerBrackets />
          <HudLabel className="self-start">Readiness</HudLabel>
          <ReadinessRing score={today.readiness.score} max={today.readiness.max} level={today.readiness.level} />
          <div className="grid w-full grid-cols-3 gap-2 text-center">
            {today.vitals.map((v) => (
              <div key={v.label} className="flex flex-col gap-0.5">
                <span className="font-mono text-base">{v.value}</span>
                <span className="text-muted-foreground text-xs">{v.label}</span>
                <span className="text-muted-foreground font-mono text-[10px]">{v.note}</span>
              </div>
            ))}
          </div>
          <div className="bg-muted flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm">
            <span className="text-muted-foreground">Mood yesterday</span>
            <span>{today.moodYesterday}</span>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Suggestions for today</CardTitle>
            <CardAction>
              <span className="text-success font-mono text-[11px]">✓ CHECKED · {today.critic.toolCalls} TOOL CALLS</span>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {suggestionsToday.map((s) => (
              <SuggestionItem key={s.id} {...s} />
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Today&apos;s schedule</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2.5">
            {schedule.map((item) => (
              <ScheduleRow key={item.start} item={item} />
            ))}
          </CardContent>
        </Card>

        <Card className="border-warning/45">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TriangleAlert className="text-warning size-5" aria-hidden="true" /> Heads up this week
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-4">
            <p className="text-[15px] leading-relaxed">{today.headsUp.text}</p>
            <Button asChild variant="outline" size="lg" className="mt-auto w-fit">
              <Link href="/week">
                See week ahead <ArrowRight />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <AskBox />
    </div>
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
