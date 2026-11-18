/**
 * Mock data for the UI while the backend is being built.
 * Sources (per CLAUDE.md): iCloud Calendar + Apple Watch / Health app.
 * All values are synthetic. Never put real personal data in this file.
 * The demo "today" is Monday, Nov 16, 2026.
 */

export type Tone = "primary" | "success" | "warning" | "destructive" | "muted";

export const agentStatus = {
  online: true,
  lastSync: "07:58",
  sources: ["Apple Watch", "iCloud Calendar"],
};

/** Shown in the greeting. */
export const profile = { name: "Trinh" };

// ---------- Weekly report  (GET /api/report?week=…) ----------

export type Mood = "pleasant" | "neutral" | "unpleasant";

/** The JSON returned by GET /api/report (backend/data/report.py). null = no data that day. */
export type Report = {
  label: string;
  stats: { label: string; value: string; suffix?: string | null; delta: string; tone: Tone }[];
  days: string[];
  sleepThis: (number | null)[];
  sleepLast: (number | null)[];
  readinessThis: (number | null)[];
  moodThis: (Mood | null)[];
  timeUse: { category: string; hours: number; delta: string }[];
  changes: { title: string; body: string }[];
  followUps: { id: number; suggestion: string; result: string; tone: Tone; detail: string }[];
};

export const report: Report = {
  label: "NOV 9 – 15 vs NOV 2 – 8",
  stats: [
    { label: "Avg sleep", value: "6h 52m", delta: "+20m", tone: "success" as Tone },
    { label: "Avg readiness", value: "6.1", suffix: "/10", delta: "+0.7", tone: "success" as Tone },
    { label: "Avg HRV", value: "50", suffix: "ms", delta: "+3 ms", tone: "success" as Tone },
    { label: "Avg steps", value: "7,840", delta: "−610", tone: "warning" as Tone },
    { label: "Workouts", value: "4", delta: "+1", tone: "success" as Tone },
    { label: "Pleasant days", value: "5", suffix: "/7", delta: "+2", tone: "success" as Tone },
  ],
  days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  sleepThis: [6.9, 7.3, 6.2, 5.8, 7.1, 7.6, 7.2],
  sleepLast: [6.5, 6.1, 6.8, 5.4, 6.6, 7.4, 6.9],
  readinessThis: [7, 7, 6, 4, 5, 7, 7],
  moodThis: ["pleasant", "pleasant", "neutral", "unpleasant", "pleasant", "pleasant", "pleasant"],
  timeUse: [
    { category: "Class", hours: 12, delta: "0" },
    { category: "Study", hours: 10, delta: "+3" },
    { category: "Work", hours: 9, delta: "0" },
    { category: "Social", hours: 6, delta: "−2" },
    { category: "Gym", hours: 4.5, delta: "+1" },
  ],
  changes: [
    {
      title: "Readiness up 0.7",
      body: "You slept 20 more minutes a night and had 1 late event instead of 4.",
    },
    {
      title: "Steps down 610 a day",
      body: "Fewer free gaps between events: 3 this week vs 7 last week.",
    },
  ],
  followUps: [
    {
      id: 31,
      suggestion: "Lights out by 11:15 before busy days",
      result: "Worked",
      tone: "success" as Tone,
      detail: "Readiness on busy days +1.1 · n = 14",
    },
    {
      id: 33,
      suggestion: "Walk in free gaps on class days",
      result: "Too early",
      tone: "muted" as Tone,
      detail: "Steps on class days +1,900 · n = 6, needs 14",
    },
    {
      id: 28,
      suggestion: "Move gym before 6pm",
      result: "No change",
      tone: "warning" as Tone,
      detail: "Next-day mood −2 pts · n = 14",
    },
  ],
};

// ---------- Ask ----------

export const suggestedQuestions = ["How's my week looking?", "Why was last week better?", "When should I work out this week?"];
