"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CoreMark, HudLabel } from "@/components/hud";
import { recentChats, sampleRun } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "agent"; text: string };

const MOCK_REPLY =
  "Mock mode: the agent backend isn’t connected yet, so I can’t run tools on this question. Once /api/chat is live, this will stream a real answer with its trace.";

export function Chat() {
  const params = useSearchParams();
  const initial = params.get("q");
  const [extra, setExtra] = useState<Msg[]>(
    initial && initial !== sampleRun.question
      ? [
          { role: "user", text: initial },
          { role: "agent", text: MOCK_REPLY },
        ]
      : [],
  );
  const [draft, setDraft] = useState("");
  const [approval, setApproval] = useState<"pending" | "approved" | "denied">("pending");

  function send() {
    const text = draft.trim();
    if (!text) return;
    setExtra((m) => [...m, { role: "user", text }, { role: "agent", text: MOCK_REPLY }]);
    setDraft("");
  }

  const run = sampleRun;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 xl:flex-row">
      <section aria-label="Conversation" className="flex min-w-0 flex-1 flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1.5">
            <span className="hud-label text-primary">Ask</span>
            <h1 className="text-2xl font-semibold tracking-tight">{run.title}</h1>
          </div>
          <span className="text-muted-foreground font-mono text-[11px]">
            run #{String(run.id).padStart(4, "0")} · {run.steps} steps · {run.seconds}s
          </span>
        </header>

        <UserBubble text={run.question} />

        <AgentTurn>
          <p className="text-[15px] leading-relaxed">{run.answerIntro}</p>

          <div className="bg-card flex flex-col gap-3.5 rounded-xl border p-5">
            <HudLabel>
              Week over week · {run.comparison.periodA} vs {run.comparison.periodB}
            </HudLabel>
            <div className="grid grid-cols-[110px_minmax(0,1fr)_64px] items-center gap-x-3.5 gap-y-3 text-[13px] sm:grid-cols-[130px_minmax(0,1fr)_72px]">
              {run.comparison.rows.map((row) => (
                <ComparisonRow key={row.label} {...row} />
              ))}
            </div>
            <div className="text-muted-foreground flex gap-4 text-xs">
              <Legend className="bg-chart-4" label={run.comparison.periodA} />
              <Legend className="bg-primary" label={run.comparison.periodB} />
            </div>
          </div>

          <p className="text-[15px] leading-relaxed">{run.answerOutro}</p>

          <div
            className={cn(
              "flex flex-col gap-3 rounded-xl border p-4",
              approval === "pending" && "border-warning/50 bg-warning/5",
              approval === "approved" && "border-success/50 bg-success/5",
              approval === "denied" && "bg-muted/40",
            )}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span
                className={cn(
                  "hud-label",
                  approval === "pending" && "text-warning",
                  approval === "approved" && "text-success",
                )}
              >
                {approval === "pending" && `Approval needed · ${run.approval.tool} ×${run.approval.count}`}
                {approval === "approved" && `Approved · ${run.approval.count} events queued`}
                {approval === "denied" && "Denied · nothing was written"}
              </span>
              <span className="text-muted-foreground font-mono text-[11px]">{run.approval.tier}</span>
            </div>
            <p className="text-sm">{run.approval.description}</p>
            {approval === "pending" ? (
              <div className="flex flex-wrap gap-2.5">
                <Button size="lg" onClick={() => setApproval("approved")}>
                  <Check /> Approve
                </Button>
                <Button size="lg" variant="outline">
                  <Pencil /> Edit
                </Button>
                <Button size="lg" variant="ghost" className="text-muted-foreground" onClick={() => setApproval("denied")}>
                  <X /> Deny
                </Button>
              </div>
            ) : (
              <Button variant="link" className="h-auto w-fit px-0" onClick={() => setApproval("pending")}>
                Undo
              </Button>
            )}
          </div>
        </AgentTurn>

        {extra.map((m, i) =>
          m.role === "user" ? (
            <UserBubble key={i} text={m.text} />
          ) : (
            <AgentTurn key={i}>
              <p className="text-muted-foreground text-[15px] leading-relaxed">{m.text}</p>
            </AgentTurn>
          ),
        )}

        <form
          className="bg-card border-primary/35 sticky bottom-4 mt-auto flex gap-2.5 rounded-xl border p-2.5"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <label htmlFor="msg" className="sr-only">Message</label>
          <Input
            id="msg"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask a follow-up…"
            className="border-transparent bg-transparent text-[15px]"
          />
          <Button type="submit" className="h-11 px-5">Send</Button>
        </form>
      </section>

      <aside aria-label="Agent trace" className="flex shrink-0 flex-col gap-4 xl:w-[340px]">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-[0.08em]">AGENT TRACE</h2>
          <span className="text-success font-mono text-[11px]">● complete</span>
        </div>
        <ol className="flex flex-col gap-2.5 font-mono text-xs">
          {run.trace.map((step, i) => (
            <li
              key={step.tool}
              className={cn(
                "flex flex-col gap-1.5 rounded-lg border p-3",
                step.critic ? "border-success/45 bg-success/5" : "bg-card",
              )}
            >
              <div className="flex justify-between gap-2">
                <span className={step.critic ? "text-success" : "text-primary"}>
                  {String(i + 1).padStart(2, "0")} {step.tool}
                </span>
                <span className="text-muted-foreground">{step.seconds}s</span>
              </div>
              <span className="text-muted-foreground">{step.summary}</span>
            </li>
          ))}
        </ol>

        <div className="text-muted-foreground flex flex-col gap-2 rounded-lg border p-3.5 font-mono text-[11px]">
          <span className="tracking-[0.12em]">PERMISSIONS</span>
          <PermRow name="read" value="auto" tone="text-success" />
          <PermRow name="write_internal" value="auto · logged" tone="text-success" />
          <PermRow name="write_external" value="ask first" tone="text-warning" />
        </div>

        <div className="flex flex-col gap-2">
          <HudLabel>Recent</HudLabel>
          {recentChats.map((c, i) => (
            <Badge key={c} variant={i === 0 ? "secondary" : "outline"} className="h-8 w-full justify-start rounded-lg font-sans text-[13px] tracking-normal">
              {c}
            </Badge>
          ))}
        </div>
      </aside>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="bg-muted max-w-xl self-end rounded-[14px_14px_4px_14px] px-4 py-3.5 text-[15px] leading-relaxed">
      {text}
    </div>
  );
}

function AgentTurn({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3.5">
      <CoreMark className="size-8" />
      <div className="flex min-w-0 flex-1 flex-col gap-3.5">{children}</div>
    </div>
  );
}

function ComparisonRow({ label, a, b, delta }: { label: string; a: number; b: number; delta: string }) {
  return (
    <>
      <span>{label}</span>
      <div className="flex flex-col gap-1" role="img" aria-label={`${label}: changed ${delta}`}>
        <div className="bg-chart-4 h-2 rounded" style={{ width: `${a * 100}%` }} />
        <div className="bg-primary h-2 rounded" style={{ width: `${b * 100}%` }} />
      </div>
      <span className="text-warning font-mono">{delta}</span>
    </>
  );
}

function Legend({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("size-2.5 rounded-sm", className)} aria-hidden="true" />
      {label}
    </span>
  );
}

function PermRow({ name, value, tone }: { name: string; value: string; tone: string }) {
  return (
    <div className="flex justify-between">
      <span>{name}</span>
      <span className={tone}>{value}</span>
    </div>
  );
}
