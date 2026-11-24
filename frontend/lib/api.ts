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

// ---------- Week + Today  (GET /api/forecast, GET /api/brief, backend/agent/briefing.py) ----------

export type Risk = "Low" | "Medium" | "High";

/** A suggestion on the Week or Today page. `track` is saved for follow-up when the user adds it. */
export type PageSuggestion = {
  id: string;
  title: string;
  time: string | null;
  why: string;
  evidence: string;
  ics: IcsFile | null;
  track: { text: string; metric: string; direction: "up" | "down"; start_date: string };
  /** Where it would go on the Week calendar (24-hour times). Only Week suggestions have one. */
  slot?: { date: string; start: string; end: string } | null;
};

export type Category = "class" | "work" | "study" | "gym" | "social" | "other";

/** One event on the Week calendar. start/end are 24-hour HH:MM for positioning; `time` is the 12-hour label. */
export type CalendarBlock = {
  id: number;
  title: string;
  category: Category;
  allDay: boolean;
  start: string | null;
  end: string | null;
  time: string;
  mine: boolean; // added or edited by you on the Week page
  editable: boolean; // false for past days (the agent's history)
};

// ---------- Editing the schedule  (POST/PUT/DELETE /api/events, backend/data/schedule.py) ----------

export type EventInput = { title: string; date: string; start: string; end: string; category: Category };

/** Called from the browser. `id` null adds a new event; otherwise it edits that one. */
export async function saveEvent(id: number | null, event: EventInput): Promise<void> {
  const res = await fetch(id === null ? "/api/events" : `/api/events/${id}`, {
    method: id === null ? "POST" : "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error ?? `Saving failed (${res.status}).`);
}

export async function deleteEvent(id: number): Promise<void> {
  const res = await fetch(`/api/events/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error ?? `Deleting failed (${res.status}).`);
}

export type ForecastDay = {
  label: string;
  date: string;
  iso: string;
  booked: number;
  readiness: number | null;
  risk: Risk;
  note: string | null;
  today: boolean;
  events: CalendarBlock[];
};

export type WeekForecast = {
  label: string;
  similarDays: number;
  usualReadiness: number | null;
  days: ForecastDay[];
  factors: { cause: string; effect: string; size: string; n: number; early: boolean }[];
  adjustments: PageSuggestion[];
  toolCalls: number;
  notes: string[];
};

export type ScheduleItem = { start: string; end: string; title: string; kind: "event" | "suggested" };

export type Brief = {
  date: string;
  dateLabel: string;
  health: {
    asOf: string;
    readiness: { score: number; max: number; level: string };
    vitals: { label: string; value: string; note: string }[];
    mood: string | null;
  } | null;
  schedule: ScheduleItem[];
  suggestions: PageSuggestion[];
  headsUp: { day: string; text: string } | null;
  toolCalls: number;
};

export async function getForecast(): Promise<WeekForecast> {
  const res = await fetch(`${BACKEND}/api/forecast`);
  if (!res.ok) throw new Error(`forecast failed: ${res.status}`);
  return res.json();
}

export async function getBrief(): Promise<Brief> {
  const res = await fetch(`${BACKEND}/api/brief`);
  if (!res.ok) throw new Error(`brief failed: ${res.status}`);
  return res.json();
}

/** Called from the browser when the user adds a suggestion, so the agent can follow up on it. */
export async function trackSuggestion(track: PageSuggestion["track"]): Promise<{ check_on: string }> {
  const res = await fetch("/api/suggestions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(track),
  });
  if (!res.ok) throw new Error(`saving the suggestion failed: ${res.status}`);
  return res.json();
}

/** Hands the browser an .ics file to open in the user's calendar app. */
export function downloadIcs(file: IcsFile) {
  const url = URL.createObjectURL(new Blob([file.ics], { type: "text/calendar" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: file.filename });
  link.click();
  URL.revokeObjectURL(url);
}
