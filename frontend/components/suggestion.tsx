import { CalendarPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** One agent suggestion: what to do, why (with evidence), and an optional .ics add. */
export function SuggestionItem({
  time,
  title,
  why,
  evidence,
  ics,
  className,
}: {
  time?: string;
  title: string;
  why: string;
  evidence?: string;
  ics: boolean;
  className?: string;
}) {
  return (
    <div className={cn("bg-muted flex flex-col gap-3 rounded-lg p-4 sm:flex-row sm:items-center", className)}>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-[15px] font-semibold">{title}</span>
          {time && <span className="text-primary font-mono text-xs">{time}</span>}
        </div>
        <p className="text-muted-foreground text-[13px] leading-relaxed">
          {why}{" "}
          {evidence && <span className="font-mono text-xs">{evidence}</span>}
        </p>
      </div>
      {ics && (
        <Button variant="outline" className="shrink-0 bg-transparent">
          <CalendarPlus /> Add to calendar
        </Button>
      )}
    </div>
  );
}
