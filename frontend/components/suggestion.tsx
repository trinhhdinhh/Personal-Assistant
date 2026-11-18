"use client";

import { useState } from "react";
import { CalendarPlus, Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadIcs, trackSuggestion, type PageSuggestion } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * One suggestion: what to do, why (with its evidence), and a way to take it.
 * "Add to calendar" downloads the .ics file; nothing touches the calendar on its own.
 * Taking a suggestion also saves it, so the agent can check a week later whether it helped.
 */
export function SuggestionItem({ suggestion, className }: { suggestion: PageSuggestion; className?: string }) {
  const { title, time, why, evidence, ics, track } = suggestion;
  const [state, setState] = useState<"new" | "saving" | "taken" | "error">("new");
  const [checkOn, setCheckOn] = useState<string | null>(null);

  async function take() {
    if (ics) downloadIcs(ics);
    setState("saving");
    try {
      const saved = await trackSuggestion(track);
      setCheckOn(saved.check_on);
      setState("taken");
    } catch {
      setState("error");
    }
  }

  return (
    <div className={cn("bg-muted flex flex-col gap-3 rounded-lg p-4 sm:flex-row sm:items-center", className)}>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-[15px] font-semibold">{title}</span>
          {time && <span className="text-primary font-mono text-xs">{time}</span>}
        </div>
        <p className="text-muted-foreground text-[13px] leading-relaxed">
          {why} <span className="font-mono text-xs">{evidence}</span>
        </p>
        {state === "taken" && checkOn && (
          <p className="text-success text-[12px]">Saved. The agent will check on {checkOn} whether it helped.</p>
        )}
        {state === "error" && <p className="text-destructive text-[12px]">Couldn&apos;t save it for follow-up.</p>}
      </div>
      {state === "taken" ? (
        <span className="text-success flex shrink-0 items-center gap-1.5 text-sm"><Check className="size-4" /> Added</span>
      ) : (
        <Button variant="outline" className="shrink-0 bg-transparent" disabled={state === "saving"} onClick={take}>
          {ics ? <><CalendarPlus /> Add to calendar</> : <><Check /> I&apos;ll do this</>}
        </Button>
      )}
    </div>
  );
}
