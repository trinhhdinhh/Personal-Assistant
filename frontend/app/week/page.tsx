import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageHeader } from "@/components/hud";
import { SuggestionItem } from "@/components/suggestion";
import { WeekCalendar } from "@/components/week-calendar";
import { getForecast, type ForecastDay, type Risk, type WeekForecast } from "@/lib/api";
import { cn } from "@/lib/utils";

const riskBadge: Record<Risk, "success" | "warning" | "destructive"> = {
  Low: "success",
  Medium: "warning",
  High: "destructive",
};

const MAX_BOOKED = 10;
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function monthOf(iso: string) {
  return MONTHS[Number(iso.slice(5, 7)) - 1];
}

export default function WeekPage() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Suspense fallback={<PageHeader eyebrow="Week ahead" title="How your week will probably go" description="Loading your forecast…" />}>
        <WeekContent />
      </Suspense>
    </div>
  );
}

async function WeekContent() {
  let forecast: WeekForecast;
  try {
    forecast = await getForecast();
  } catch {
    return (
      <PageHeader
        eyebrow="Week ahead"
        title="Forecast unavailable"
        description="Couldn't reach the backend. Start it with `python manage.py runserver` and reload."
      />
    );
  }
  return <WeekView forecast={forecast} />;
}

function WeekView({ forecast }: { forecast: WeekForecast }) {
  return (
    <>
      <PageHeader
        eyebrow={`Week ahead · ${forecast.label}`}
        title="How your week will probably go"
        description={`Predicted from your calendar and ${forecast.similarDays} days of your own history.`}
        actions={<Badge variant="success" className="h-8">FROM YOUR DATA · {forecast.toolCalls} TOOL CALLS</Badge>}
      />

      <section aria-label="Daily forecast" className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {forecast.days.map((d) => (
          <DayCard key={d.iso} day={d} />
        ))}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Your week on the calendar</CardTitle>
          <CardDescription>Every booked hour, drawn where it falls. Dashed blocks are suggestions.</CardDescription>
        </CardHeader>
        <CardContent>
          <WeekCalendar days={forecast.days} suggestions={forecast.adjustments} />
        </CardContent>
      </Card>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Suggested changes</CardTitle>
            <CardDescription>Nothing changes unless you add it.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {forecast.adjustments.length ? (
              forecast.adjustments.map((a) => <SuggestionItem key={a.id} suggestion={a} />)
            ) : (
              <p className="text-muted-foreground text-sm">No rough days ahead, so nothing to change.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Why these predictions</CardTitle>
            <CardAction>
              <span className="text-muted-foreground font-mono text-xs">your history</span>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Affects</TableHead>
                  <TableHead className="text-right">Change</TableHead>
                  <TableHead className="text-right">n</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {forecast.factors.map((f) => (
                  <TableRow key={f.cause}>
                    <TableCell>{f.cause}</TableCell>
                    <TableCell className="text-muted-foreground">{f.effect}</TableCell>
                    <TableCell className="text-right font-mono">{f.size}</TableCell>
                    <TableCell className="text-muted-foreground text-right font-mono">
                      {f.n}
                      {f.early && <span className="text-warning" title="Under 14 days: early and uncertain"> *</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-muted-foreground text-[13px]">
              Links in your own data, not causes or guarantees.
              {forecast.factors.some((f) => f.early) && " * Under 14 days, so early and uncertain."}
            </p>
          </CardContent>
        </Card>
      </section>
    </>
  );
}

function DayCard({ day }: { day: ForecastDay }) {
  const pct = Math.min(100, Math.round((day.booked / MAX_BOOKED) * 100));
  return (
    <div
      className={cn(
        "bg-card flex flex-col gap-3 rounded-xl border p-4",
        day.risk === "High" && "border-destructive/50",
        day.today && "border-primary/50",
      )}
    >
      <div className="flex items-baseline justify-between">
        <span className="font-semibold">{day.label}</span>
        <span className="text-muted-foreground font-mono text-xs">{day.today ? "TODAY" : `${monthOf(day.iso)} ${day.date}`}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-3xl">
          {day.readiness ?? "–"}
          <span className="text-muted-foreground text-sm">/10</span>
        </span>
        <span className="text-muted-foreground text-xs">predicted readiness</span>
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Booked</span>
          <span className="font-mono">{day.booked}h</span>
        </div>
        <div className="bg-muted h-1.5 rounded-full" role="img" aria-label={`${day.booked} hours booked`}>
          <div className="bg-chart-1 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <Badge variant={riskBadge[day.risk]}>{day.risk.toUpperCase()} RISK</Badge>
      {day.note && <p className="text-muted-foreground text-xs leading-snug">{day.note}</p>}
    </div>
  );
}
