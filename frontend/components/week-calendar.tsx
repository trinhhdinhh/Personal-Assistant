"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { EventEditor, type Draft } from "@/components/event-editor";
import { Button } from "@/components/ui/button";
import type { CalendarBlock, ForecastDay, PageSuggestion } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * A week view of the calendar: one column per day, each event drawn at its real time and length.
 * Click an empty spot to add an event there, or click an event to edit or delete it.
 * After a change the page reloads its data, so the forecast above updates too.
 */

const HOUR_PX = 44; // height of one hour on the grid
const BUSY_HOURS = 7; // same line the forecast uses for a busy day
const LATE = "21:30"; // same line the forecast uses for a late event

const CATEGORY_COLOR: Record<CalendarBlock["category"], string> = {
  class: "var(--chart-1)",
  study: "var(--chart-2)",
  work: "var(--warning)",
  gym: "var(--success)",
  social: "#f27fc4",
  other: "var(--muted-foreground)",
};

const CATEGORY_LABEL: Record<CalendarBlock["category"], string> = {
  class: "Class",
  study: "Study",
  work: "Work",
  gym: "Gym",
  social: "Social",
  other: "Other",
};

/** "14:30" → minutes after midnight. */
function minutes(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

/** An event's start and end in minutes. One that runs past midnight is cut off at midnight. */
function span(start: string, end: string) {
  const from = minutes(start);
  const to = minutes(end);
  return { from, to: to <= from ? 24 * 60 : to };
}

/** Minutes after midnight → "14:30". */
function hhmm(mins: number) {
  const m = Math.min(Math.max(mins, 0), 23 * 60 + 59);
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

function hourLabel(hour: number) {
  if (hour === 0 || hour === 24) return "12 AM";
  if (hour === 12) return "12 PM";
  return hour < 12 ? `${hour} AM` : `${hour - 12} PM`;
}

export function WeekCalendar({ days, suggestions }: { days: ForecastDay[]; suggestions: PageSuggestion[] }) {
  // Show 7 AM to midnight, stretched if anything falls outside that.
  const spans = days.flatMap((d) => d.events.filter((e) => !e.allDay).map((e) => span(e.start!, e.end!)));
  const firstHour = Math.min(7, ...spans.map((s) => Math.floor(s.from / 60)));
  const lastHour = Math.max(24, ...spans.map((s) => Math.ceil(s.to / 60)));
  const hours = Array.from({ length: lastHour - firstHour + 1 }, (_, i) => firstHour + i);
  const top = (mins: number) => ((mins - firstHour * 60) / 60) * HOUR_PX;
  const height = (lastHour - firstHour) * HOUR_PX;
  const usedCategories = new Set(days.flatMap((d) => d.events.map((e) => e.category)));

  const router = useRouter();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [refreshing, startRefresh] = useTransition();
  const dayOptions = days.map((d) => ({ iso: d.iso, label: `${d.label} ${d.date}` }));

  /** A new one-hour event starting at the clicked half hour. */
  function addAt(day: ForecastDay, clickY: number) {
    const clicked = firstHour * 60 + (clickY / HOUR_PX) * 60;
    const start = Math.floor(clicked / 30) * 30;
    setDraft({ id: null, title: "", date: day.iso, start: hhmm(start), end: hhmm(start + 60), category: "other" });
  }

  function edit(day: ForecastDay, e: CalendarBlock) {
    setDraft({ id: e.id, title: e.title, date: day.iso, start: e.start!, end: e.end!, category: e.category });
  }

  function saved() {
    setDraft(null);
    startRefresh(() => router.refresh());
  }

  return (
    <div className={cn("flex flex-col gap-4 transition-opacity", refreshing && "opacity-60")}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Legend categories={Object.keys(CATEGORY_LABEL).filter((c) => usedCategories.has(c as CalendarBlock["category"])) as CalendarBlock["category"][]} />
        <Button
          variant="outline"
          size="sm"
          onClick={() => setDraft({ id: null, title: "", date: days[0].iso, start: "12:00", end: "13:00", category: "other" })}
        >
          <Plus /> Add event
        </Button>
      </div>

      <div className="overflow-x-auto">
        <div className="grid min-w-190 grid-cols-[3.5rem_repeat(7,minmax(0,1fr))] pb-2">
          {/* Header row: day name and how many hours are booked */}
          <div />
          {days.map((d) => (
            <DayHeader key={d.iso} day={d} />
          ))}

          {/* Time gutter */}
          <div className="relative" style={{ height }}>
            {hours.map((h) => (
              <span
                key={h}
                className="text-muted-foreground absolute right-2 -translate-y-1/2 font-mono text-[10px]"
                style={{ top: top(h * 60) }}
              >
                {hourLabel(h)}
              </span>
            ))}
          </div>

          {/* One column per day */}
          {days.map((d) => (
            <div
              key={d.iso}
              className={cn("relative cursor-copy border-l", d.today && "bg-primary/4")}
              style={{ height }}
              onClick={(ev) => addAt(d, ev.clientY - ev.currentTarget.getBoundingClientRect().top)}
              title="Click to add an event"
            >
              {hours.map((h) => (
                <div key={h} className="border-border/60 absolute inset-x-0 border-t" style={{ top: top(h * 60) }} />
              ))}
              <div
                className="border-warning/50 absolute inset-x-0 border-t border-dashed"
                style={{ top: top(minutes(LATE)) }}
                title="Events ending after 9:30 PM count as late"
              />

              {d.events
                .filter((e) => !e.allDay)
                .map((e) => {
                  const s = span(e.start!, e.end!);
                  return (
                    <Block
                      key={e.id}
                      title={e.title}
                      time={e.time}
                      top={top(s.from)}
                      height={top(s.to) - top(s.from)}
                      color={CATEGORY_COLOR[e.category]}
                      mine={e.mine}
                      onClick={e.editable ? () => edit(d, e) : undefined}
                    />
                  );
                })}

              {suggestions
                .filter((sg) => sg.slot?.date === d.iso)
                .map((sg) => {
                  const s = span(sg.slot!.start, sg.slot!.end);
                  return (
                    <Block
                      key={sg.id}
                      title={sg.title}
                      time={sg.time ?? ""}
                      top={top(s.from)}
                      height={top(s.to) - top(s.from)}
                      suggested
                    />
                  );
                })}
            </div>
          ))}
        </div>
      </div>

      <p className="text-muted-foreground text-xs">
        Click an empty spot to add an event, or click an event to edit it. Events with a dot are ones you added or
        changed.
      </p>

      {draft && <EventEditor key={`${draft.id}-${draft.date}-${draft.start}`} draft={draft} days={dayOptions} onClose={() => setDraft(null)} onSaved={saved} />}
    </div>
  );
}

function DayHeader({ day }: { day: ForecastDay }) {
  const busy = day.booked >= BUSY_HOURS;
  const allDay = day.events.filter((e) => e.allDay);
  return (
    <div className={cn("flex flex-col gap-1 border-b border-l px-2 pb-2", day.today && "bg-primary/4")}>
      <div className="flex items-baseline justify-between gap-1">
        <span className={cn("text-sm font-semibold", day.today && "text-primary")}>
          {day.label} {day.date}
        </span>
        <span className={cn("font-mono text-[11px]", busy ? "text-warning" : "text-muted-foreground")}>{day.booked}h</span>
      </div>
      <div className="bg-muted h-1 rounded-full" role="img" aria-label={`${day.booked} hours booked`}>
        <div
          className={cn("h-1 rounded-full", busy ? "bg-warning" : "bg-chart-1")}
          style={{ width: `${Math.min(100, (day.booked / 10) * 100)}%` }}
        />
      </div>
      {allDay.map((e) => (
        <span key={e.title} className="bg-muted truncate rounded px-1.5 py-0.5 text-[10px]" title={e.title}>
          {e.title}
        </span>
      ))}
    </div>
  );
}

function Block({
  title,
  time,
  top,
  height,
  color,
  suggested = false,
  mine = false,
  onClick,
}: {
  title: string;
  time: string;
  top: number;
  height: number;
  color?: string;
  suggested?: boolean;
  mine?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={(ev) => {
        ev.stopPropagation(); // don't also start a new event in the column underneath
        onClick?.();
      }}
      onKeyDown={(ev) => onClick && (ev.key === "Enter" || ev.key === " ") && (ev.preventDefault(), onClick())}
      className={cn(
        "absolute inset-x-1 cursor-default overflow-hidden rounded-md px-1.5 py-1 leading-tight",
        suggested ? "border-primary/70 bg-primary/10 text-primary border border-dashed" : "border-l-[3px]",
        onClick && "focus-visible:ring-ring cursor-pointer hover:brightness-125 focus-visible:ring-2 focus-visible:outline-none",
      )}
      style={
        suggested
          ? { top, height: Math.max(height, 18) }
          : { top, height, borderLeftColor: color, background: `color-mix(in oklab, ${color} 22%, transparent)` }
      }
      title={`${title} · ${time}`}
    >
      <p className="flex items-center gap-1 text-[11px] font-medium">
        <span className="truncate">{title}</span>
        {mine && <span className="bg-primary size-1.5 shrink-0 rounded-full" aria-label="added by you" />}
      </p>
      {height >= 34 && <p className="text-muted-foreground truncate font-mono text-[10px]">{time}</p>}
    </div>
  );
}

function Legend({ categories }: { categories: CalendarBlock["category"][] }) {
  return (
    <div className="text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
      {categories.map((c) => (
        <span key={c} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: CATEGORY_COLOR[c] }} />
          {CATEGORY_LABEL[c]}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="border-primary/70 bg-primary/10 size-2.5 rounded-sm border border-dashed" />
        Suggested
      </span>
      <span className="flex items-center gap-1.5">
        <span className="border-warning/70 w-4 border-t border-dashed" />
        9:30 PM (late)
      </span>
    </div>
  );
}
