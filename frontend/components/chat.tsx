"use client";

import { Fragment, Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarPlus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CoreMark, HudLabel } from "@/components/hud";
import { askAgent, type ChatRun, type ChatTurn, type IcsFile } from "@/lib/api";
import { suggestedQuestions } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type Turn = { id: number; question: string; run?: ChatRun; error?: string };

const STOP_NOTE: Partial<Record<ChatRun["stop"], string>> = {
  step_limit: "The agent hit its step limit, so this answer uses what it found so far.",
  cut_off: "The answer was cut off.",
  declined: "The model declined this question.",
  error: "Something went wrong reaching the model.",
};

export function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const busy = turns.some((t) => !t.run && !t.error);
  const latest = turns.at(-1);

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    // Earlier answered turns become context for follow-up questions.
    const history: ChatTurn[] = turns.flatMap((t) =>
      t.run && (t.run.stop === "answered" || t.run.stop === "step_limit")
        ? [{ role: "user", content: t.question }, { role: "assistant", content: t.run.answer }]
        : [],
    );
    const id = Date.now();
    setTurns((all) => [...all, { id, question }]);
    setDraft("");
    try {
      const run = await askAgent(question, history);
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, run } : t)));
    } catch (e) {
      const error = e instanceof Error ? e.message : "Something went wrong.";
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, error } : t)));
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 xl:flex-row">
      <section aria-label="Conversation" className="flex min-w-0 flex-1 flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1.5">
            <span className="hud-label text-primary">Ask</span>
            <h1 className="text-2xl font-semibold tracking-tight">Ask about your life</h1>
          </div>
          {latest?.run && (
            <span className="text-muted-foreground font-mono text-[11px]">
              {latest.run.steps.length} steps · {latest.run.seconds}s · {latest.run.model}
            </span>
          )}
        </header>

        <Suspense fallback={null}>
          <QuestionFromUrl onQuestion={send} />
        </Suspense>

        {turns.length === 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-muted-foreground text-[15px]">
              Ask anything about your schedule, sleep, recovery or mood. The agent answers from your own data and
              shows every step it took.
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((q) => (
                <Button key={q} variant="outline" size="sm" className="h-9 rounded-full bg-transparent" onClick={() => send(q)}>
                  {q}
                </Button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t) => (
          <Fragment key={t.id}>
            <UserBubble text={t.question} />
            <AgentTurn>
              {t.error ? (
                <p className="text-destructive text-[15px]">{t.error}</p>
              ) : !t.run ? (
                <p className="text-muted-foreground animate-pulse text-[15px]">Checking your data…</p>
              ) : (
                <Answer run={t.run} />
              )}
            </AgentTurn>
          </Fragment>
        ))}

        <form
          className="bg-card border-primary/35 sticky bottom-4 mt-auto flex gap-2.5 rounded-xl border p-2.5"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
        >
          <label htmlFor="msg" className="sr-only">Message</label>
          <Input
            id="msg"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={turns.length ? "Ask a follow-up…" : "How's my week looking?"}
            className="border-transparent bg-transparent text-[15px]"
          />
          <Button type="submit" className="h-11 px-5" disabled={busy}>Ask</Button>
        </form>
      </section>

      <aside aria-label="How the agent answered" className="flex shrink-0 flex-col gap-4 xl:w-[320px]">
        <Steps turn={latest} />

        <div className="text-muted-foreground flex flex-col gap-1.5 rounded-lg border p-3.5 text-[13px]">
          <span className="hud-label">Access</span>
          <span>Reads your calendar and daily health summaries.</span>
          <span>Never changes your calendar. You add suggestions yourself.</span>
        </div>

        {turns.length > 1 && (
          <div className="flex flex-col gap-2">
            <HudLabel>This session</HudLabel>
            {turns.map((t) => (
              <span key={t.id} className="text-muted-foreground truncate rounded-lg border px-3 py-1.5 text-[13px]">
                {t.question}
              </span>
            ))}
          </div>
        )}
      </aside>
    </div>
  );
}

// ---------- the answer ----------

function Answer({ run }: { run: ChatRun }) {
  if (run.stop === "blocked") {
    return (
      <div className="border-warning/50 bg-warning/5 flex flex-col gap-2 rounded-xl border p-4">
        <span className="hud-label text-warning">Answer blocked</span>
        <p className="text-[15px] leading-relaxed">{run.answer}</p>
        <ul className="text-muted-foreground list-disc pl-5 text-[13px]">
          {run.checks.flatMap((c) => c.problems).map((p) => <li key={p}>{p}</li>)}
        </ul>
      </div>
    );
  }
  const note = STOP_NOTE[run.stop];
  return (
    <>
      <Markdown text={run.answer} />
      {note && <p className="text-muted-foreground text-[13px]">{note}</p>}
      {run.files.map((f) => <CalendarFile key={f.filename} file={f} />)}
    </>
  );
}

function CalendarFile({ file }: { file: IcsFile }) {
  const [state, setState] = useState<"new" | "added" | "dismissed">("new");

  function download() {
    const url = URL.createObjectURL(new Blob([file.ics], { type: "text/calendar" }));
    const link = Object.assign(document.createElement("a"), { href: url, download: file.filename });
    link.click();
    URL.revokeObjectURL(url);
    setState("added");
  }

  return (
    <div className={cn("flex flex-col gap-3 rounded-xl border p-4",
      state === "added" ? "border-success/50 bg-success/5" : "border-primary/45 bg-primary/5")}>
      <span className={cn("hud-label", state === "added" ? "text-success" : "text-primary")}>
        {state === "added" ? "Downloaded · open it to add to Calendar" : state === "dismissed" ? "Dismissed" : "Suggestion"}
      </span>
      <p className="text-sm">{file.summary}</p>
      {state === "new" ? (
        <div className="flex flex-wrap gap-2.5">
          <Button size="lg" onClick={download}><CalendarPlus /> Add to calendar</Button>
          <Button size="lg" variant="ghost" className="text-muted-foreground" onClick={() => setState("dismissed")}>
            <X /> Dismiss
          </Button>
        </div>
      ) : (
        <Button variant="link" className="h-auto w-fit px-0" onClick={() => setState("new")}>Undo</Button>
      )}
    </div>
  );
}

/** Just enough Markdown for the agent's answers: paragraphs, bullet/numbered lists, **bold**. */
function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  return (
    <div className="flex flex-col gap-3 text-[15px] leading-relaxed">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        if (lines.every((l) => /^\s*[-*]\s/.test(l))) {
          return <ul key={i} className="list-disc space-y-1 pl-5">{lines.map((l, j) => <li key={j}><Inline text={l.replace(/^\s*[-*]\s/, "")} /></li>)}</ul>;
        }
        if (lines.every((l) => /^\s*\d+[.)]\s/.test(l))) {
          return <ol key={i} className="list-decimal space-y-1 pl-5">{lines.map((l, j) => <li key={j}><Inline text={l.replace(/^\s*\d+[.)]\s/, "")} /></li>)}</ol>;
        }
        return <p key={i}>{lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}<Inline text={l} /></Fragment>)}</p>;
      })}
    </div>
  );
}

function Inline({ text }: { text: string }) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  );
}

// ---------- the steps panel ----------

function Steps({ turn }: { turn?: Turn }) {
  const run = turn?.run;
  const status = !turn ? "idle" : turn.error ? "error" : !run ? "working" : "complete";
  const passed = run?.checks.filter((c) => c.passed).length ?? 0;
  const allPassed = run ? passed === run.checks.length : false;

  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-[0.08em]">AGENT STEPS</h2>
        <span className={cn("font-mono text-[11px]",
          status === "complete" ? "text-success" : status === "working" ? "text-primary animate-pulse" : "text-muted-foreground")}>
          ● {status}
        </span>
      </div>

      {!run ? (
        <p className="text-muted-foreground text-[13px]">
          {status === "working" ? "The agent is choosing tools and reading your data…" : "Steps appear here after you ask."}
        </p>
      ) : (
        <ol className="flex flex-col gap-2 font-mono text-xs">
          {run.steps.map((step, i) => (
            <li key={i} className={cn("flex flex-col gap-1 rounded-lg border p-3", step.ok ? "bg-card" : "border-destructive/45")}>
              <div className="flex justify-between gap-2">
                <span className={step.ok ? "text-primary" : "text-destructive"}>
                  {String(i + 1).padStart(2, "0")} {step.tool}
                </span>
                <span className="text-muted-foreground">{(step.ms / 1000).toFixed(1)}s</span>
              </div>
              <span className="text-muted-foreground">{step.summary}</span>
            </li>
          ))}
          {run.checks.length > 0 && (
            <li className={cn("flex flex-col gap-1 rounded-lg border p-3",
              allPassed ? "border-success/45 bg-success/5" : "border-warning/50 bg-warning/5")}>
              <span className={allPassed ? "text-success" : "text-warning"}>
                {String(run.steps.length + 1).padStart(2, "0")} answer checks
              </span>
              <span className="text-muted-foreground">
                {passed}/{run.checks.length} passed
                {run.retries > 0 && ` · rewritten ${run.retries}× after a failed check`}
              </span>
              {run.checks.map((c) => (
                <span key={c.name} className={c.passed ? "text-muted-foreground" : "text-warning"}>
                  {c.passed ? "✓" : "✗"} {c.name.replaceAll("_", " ")}
                </span>
              ))}
            </li>
          )}
        </ol>
      )}
      {run && (
        <span className="text-muted-foreground font-mono text-[11px]">
          {run.model_calls} model calls · {(run.tokens.input + run.tokens.output).toLocaleString()} tokens
        </span>
      )}
    </>
  );
}

// ---------- small pieces ----------

/** A question sent from the Today page arrives as ?q=… and is asked once. */
function QuestionFromUrl({ onQuestion }: { onQuestion: (q: string) => void }) {
  const q = useSearchParams().get("q");
  const asked = useRef<string | null>(null);
  useEffect(() => {
    if (q && asked.current !== q) {
      asked.current = q;
      onQuestion(q);
    }
  }, [q, onQuestion]);
  return null;
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
