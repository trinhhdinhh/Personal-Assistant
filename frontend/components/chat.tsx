"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarPlus, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CoreMark, HudLabel } from "@/components/hud";
import { forecast, recentChats, sampleRun, type Risk } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "agent"; text: string };

const MOCK_REPLY =
  "Mock mode: the agent backend isn’t connected yet. Once /api/chat is live, this will be a real answer with its steps.";

const riskText: Record<Risk, string> = {
  Low: "text-success",
  Medium: "text-warning",
  High: "text-destructive",
};

export function Chat() {
  const run = sampleRun;
  const [extra, setExtra] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [added, setAdded] = useState<"no" | "added" | "dismissed">("no");

  function send() {
    const text = draft.trim();
    if (!text) return;
    setExtra((m) => [...m, { role: "user", text }, { role: "agent", text: MOCK_REPLY }]);
    setDraft("");
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 xl:flex-row">
      <section aria-label="Conversation" className="flex min-w-0 flex-1 flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1.5">
            <span className="hud-label text-primary">Ask</span>
            <h1 className="text-2xl font-semibold tracking-tight">Ask about your life</h1>
          </div>
          <span className="text-muted-foreground font-mono text-[11px]">
            run #{run.id} · {run.steps} steps · {run.seconds}s
          </span>
        </header>

        <UserBubble text={run.question} />

        <AgentTurn>
          <p className="text-[15px] leading-relaxed">{run.answerIntro}</p>

          <div className="bg-card grid grid-cols-7 gap-1.5 rounded-xl border p-4" role="img" aria-label="Predicted readiness for each day this week">
            {forecast.days.map((d) => (
              <div key={d.date} className="flex flex-col items-center gap-1">
                <span className="text-muted-foreground font-mono text-[10px]">{d.label.toUpperCase()}</span>
                <span className="font-mono text-lg">{d.readiness}</span>
                <span className={cn("font-mono text-[10px]", riskText[d.risk])}>{d.risk.toLowerCase()}</span>
              </div>
            ))}
          </div>

          <p className="text-[15px] leading-relaxed">{run.answerOutro}</p>

          <div
            className={cn(
              "flex flex-col gap-3 rounded-xl border p-4",
              added === "added" ? "border-success/50 bg-success/5" : "border-primary/45 bg-primary/5",
            )}
          >
            <span className={cn("hud-label", added === "added" ? "text-success" : "text-primary")}>
              {added === "added" ? "Added · opened in Calendar" : added === "dismissed" ? "Dismissed" : "Suggestion"}
            </span>
            <p className="text-sm">{run.suggestion.title}</p>
            {added === "no" ? (
              <div className="flex flex-wrap gap-2.5">
                <Button size="lg" onClick={() => setAdded("added")}>
                  <CalendarPlus /> Add to calendar
                </Button>
                <Button size="lg" variant="ghost" className="text-muted-foreground" onClick={() => setAdded("dismissed")}>
                  <X /> Dismiss
                </Button>
              </div>
            ) : (
              <Button variant="link" className="h-auto w-fit px-0" onClick={() => setAdded("no")}>
                Undo
              </Button>
            )}
          </div>
        </AgentTurn>

        <Suspense fallback={null}>
          <QuestionFromUrl />
        </Suspense>

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
          <Button type="submit" className="h-11 px-5">Ask</Button>
        </form>
      </section>

      <aside aria-label="How the agent answered" className="flex shrink-0 flex-col gap-4 xl:w-[320px]">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-[0.08em]">AGENT STEPS</h2>
          <span className="text-success font-mono text-[11px]">● complete</span>
        </div>
        <ol className="flex flex-col gap-2 font-mono text-xs">
          {run.trace.map((step, i) => (
            <li
              key={step.tool}
              className={cn(
                "flex flex-col gap-1 rounded-lg border p-3",
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

        <div className="text-muted-foreground flex flex-col gap-1.5 rounded-lg border p-3.5 text-[13px]">
          <span className="hud-label">Access</span>
          <span>Reads your calendar and health summaries.</span>
          <span>Never changes your calendar. You add suggestions yourself.</span>
        </div>

        <div className="flex flex-col gap-2">
          <HudLabel>Recent</HudLabel>
          {recentChats.map((c, i) => (
            <Badge
              key={c}
              variant={i === 0 ? "secondary" : "outline"}
              className="h-8 w-full justify-start rounded-lg font-sans text-[13px] tracking-normal"
            >
              {c}
            </Badge>
          ))}
        </div>
      </aside>
    </div>
  );
}

/** A question sent from the Today page arrives as ?q=… */
function QuestionFromUrl() {
  const q = useSearchParams().get("q");
  if (!q || q === sampleRun.question) return null;
  return (
    <>
      <UserBubble text={q} />
      <AgentTurn>
        <p className="text-muted-foreground text-[15px] leading-relaxed">{MOCK_REPLY}</p>
      </AgentTurn>
    </>
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
