import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageHeader } from "@/components/hud";
import { RangeStats } from "@/components/range-stats";
import { SleepFocusScatter } from "@/components/sleep-focus-scatter";
import { correlations, downfalls, sleepFocusStats, type Tone } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const toneText: Record<Tone, string> = {
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
  muted: "text-muted-foreground",
};

export default function KnowPage() {
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <PageHeader eyebrow="Know" title="What your data says" />

      <RangeStats />

      <section className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Sleep → next-day focus</CardTitle>
            <CardAction>
              <span className="text-muted-foreground font-mono text-xs">
                r = {sleepFocusStats.r.toFixed(2)} · n = {sleepFocusStats.n}
              </span>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <SleepFocusScatter />
            <p className="text-muted-foreground text-[13px]">
              Each dot is one day. Correlation only — the Learn tab can test it.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detected downfalls</CardTitle>
            <CardAction>
              <span className="text-muted-foreground font-mono text-xs">detect_downfalls()</span>
            </CardAction>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {downfalls.map((d) => (
              <div key={d.title} className="bg-muted flex flex-col gap-1.5 rounded-lg p-3.5">
                <div className="flex justify-between gap-3">
                  <span className="text-[15px] font-semibold">{d.title}</span>
                  <span className={cn("font-mono text-xs", toneText[d.tone])}>{d.freq}</span>
                </div>
                <span className="text-muted-foreground text-[13px]">{d.detail}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Strongest links</CardTitle>
          <CardDescription>Links with under 14 days of data are hidden by the critic.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table className="min-w-[640px]">
            <TableHeader>
              <TableRow>
                <TableHead>Input</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead>Lag</TableHead>
                <TableHead>r</TableHead>
                <TableHead>n</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Action</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {correlations.map((c) => (
                <TableRow key={c.input + c.outcome}>
                  <TableCell>{c.input}</TableCell>
                  <TableCell>{c.outcome}</TableCell>
                  <TableCell className="font-mono">{c.lag}</TableCell>
                  <TableCell className={cn("font-mono", c.r >= 0 ? "text-success" : "text-destructive")}>
                    {c.r > 0 ? "+" : "−"}
                    {Math.abs(c.r).toFixed(2)}
                  </TableCell>
                  <TableCell className="font-mono">{c.n}</TableCell>
                  <TableCell className="text-right">
                    {c.status === "testing" ? (
                      <Badge variant="hud">TESTING</Badge>
                    ) : (
                      <Link href="/learn" className="text-primary text-[13px] hover:underline">
                        Test it
                      </Link>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
