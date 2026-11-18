import type { Report } from "@/lib/mock-data";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function getReport(): Promise<Report> {
  const res = await fetch(`${BACKEND}/api/report`);
  if (!res.ok) throw new Error(`report failed: ${res.status}`);
  return res.json();
}

// ---------- Ask  (POST /api/chat, backend/agent/views.py) ----------

export type AgentStep = { tool: string; input: Record<string, unknown>; ok: boolean; summary: string; ms: number };
export type AnswerCheck = { name: string; passed: boolean; problems: string[] };
export type IcsFile = { filename: string; ics: string; summary: string };
export type ChatTurn = { role: "user" | "assistant"; content: string };

export type ChatRun = {
  answer: string;
  stop: "answered" | "step_limit" | "blocked" | "cut_off" | "declined" | "error";
  steps: AgentStep[];
  checks: AnswerCheck[];
  retries: number;
  files: IcsFile[];
  model: string;
  model_calls: number;
  tokens: { input: number; output: number };
  seconds: number;
};

/** Called from the browser; goes through app/api/chat/route.ts to Django. */
export async function askAgent(question: string, history: ChatTurn[]): Promise<ChatRun> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  const data = await res.json().catch(() => ({ error: `The agent returned an error (${res.status}).` }));
  if (!res.ok) throw new Error(data.error ?? `The agent returned an error (${res.status}).`);
  return data;
}
