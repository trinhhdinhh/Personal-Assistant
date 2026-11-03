"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { statsByRange, type Range, type Tone } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const RANGES: Range[] = ["7d", "30d", "90d"];

const toneText: Record<Tone, string> = {
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
  muted: "text-muted-foreground",
};

/** Stat tiles with a 7d / 30d / 90d switcher. */
export function RangeStats() {
  return (
    <Tabs defaultValue="90d" className="gap-4">
      <TabsList aria-label="Range" className="self-end">
        {RANGES.map((r) => (
          <TabsTrigger key={r} value={r} className="min-w-14">
            {r}
          </TabsTrigger>
        ))}
      </TabsList>
      {RANGES.map((r) => (
        <TabsContent key={r} value={r} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {statsByRange[r].map((s) => (
            <div key={s.label} className="bg-card flex flex-col gap-2 rounded-xl border p-5">
              <span className="text-muted-foreground text-[13px]">{s.label}</span>
              <span className="font-mono text-3xl">
                {s.value}
                {s.suffix && <span className="text-muted-foreground text-sm"> {s.suffix}</span>}
              </span>
              <span className={cn("font-mono text-xs", toneText[s.tone])}>{s.delta}</span>
            </div>
          ))}
        </TabsContent>
      ))}
    </Tabs>
  );
}
