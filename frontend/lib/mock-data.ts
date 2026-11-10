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

// ---------- Today  (GET /api/brief) ----------

export const today = {
  dateLabel: "MON · NOV 16 · 07:30 CST",
  name: "Trinh",
  readiness: { score: 7, max: 10, level: "Ready" },
  vitals: [
    { label: "Sleep", value: "7h 12m", note: "+24m vs avg" },
    { label: "HRV", value: "48 ms", note: "baseline 52" },
    { label: "Resting HR", value: "58 bpm", note: "normal" },
  ],
  moodYesterday: "Slightly pleasant",
  critic: { toolCalls: 5 },
  headsUp: {
    day: "Thursday",
    text: "Thursday has 8h booked. After days like that your readiness the next morning averages 1.8 points lower.",
  },
};

export type Suggestion = {
  id: number;
  time?: string;
  title: string;
  why: string;
  evidence: string;
  ics: boolean;
};

export const suggestionsToday: Suggestion[] = [
  {
    id: 41,
    time: "3:00–3:45 PM",
    title: "Take a walk in your free gap",
    why: "On class days you average 3.9k steps by 3pm, vs 7.2k on other days.",
    evidence: "n = 24 days",
    ics: true,
  },
  {
    id: 42,
    time: "11:15 PM",
    title: "Lights out by 11:15 tonight",
    why: "Busy week ahead. Your sleep the night before tracks your readiness the next day.",
    evidence: "r = 0.46 · n = 41",
    ics: true,
  },
  {
    id: 43,
    time: "5:30 PM",
    title: "Keep today's gym session",
    why: "After workout days, your mood logs are pleasant 71% of the time vs 48% otherwise.",
    evidence: "n = 38 days",
    ics: false,
  },
];

export type ScheduleItem = {
  start: string;
  end: string;
  title: string;
  kind: "event" | "free" | "suggested";
};

export const schedule: ScheduleItem[] = [
  { start: "9:00", end: "10:15", title: "Class", kind: "event" },
  { start: "10:30", end: "12:00", title: "Study block", kind: "event" },
  { start: "12:30", end: "2:45", title: "Class", kind: "event" },
  { start: "3:00", end: "3:45", title: "Free · walk suggested", kind: "suggested" },
  { start: "4:00", end: "5:00", title: "Work shift", kind: "event" },
  { start: "5:30", end: "6:30", title: "Gym", kind: "event" },
];

// ---------- Week ahead  (GET /api/forecast?week=…) ----------

export type Risk = "Low" | "Medium" | "High";

export type ForecastDay = {
  label: string;
  date: string;
  booked: number; // hours
  readiness: number; // predicted 0–10
  risk: Risk;
  note?: string;
  today?: boolean;
};

export const forecast = {
  label: "NOV 16 – 22",
  similarDays: 54,
  days: [
    { label: "Mon", date: "16", booked: 6, readiness: 7, risk: "Low", today: true },
    { label: "Tue", date: "17", booked: 5.5, readiness: 7, risk: "Low" },
    { label: "Wed", date: "18", booked: 7, readiness: 6, risk: "Medium", note: "Study until 10pm" },
    { label: "Thu", date: "19", booked: 8, readiness: 4, risk: "High", note: "8h booked after a late Wed" },
    { label: "Fri", date: "20", booked: 4.5, readiness: 5, risk: "Medium", note: "Recovering from Thu" },
    { label: "Sat", date: "21", booked: 2, readiness: 8, risk: "Low" },
    { label: "Sun", date: "22", booked: 1, readiness: 8, risk: "Low" },
  ] as ForecastDay[],
  factors: [
    { cause: "7h+ booked", effect: "Next-day readiness", size: "−1.8 pts", n: 21 },
    { cause: "Events after 9pm", effect: "Sleep that night", size: "−52 min", n: 17 },
    { cause: "Sleep under 6h", effect: "Next-day readiness", size: "−2.1 pts", n: 19 },
    { cause: "Workout day", effect: "Pleasant mood next day", size: "+23 pts", n: 38 },
  ],
  adjustments: [
    { id: 44, title: "Move Wednesday's 9pm study to 4:00–5:30 PM", why: "Ends the late night before your heaviest day.", ics: true },
    { id: 45, title: "Add a 20-minute walk Thursday at 12:15", why: "Your only gap that day.", ics: true },
    { id: 46, title: "Keep Saturday morning open", why: "You recover best with an unscheduled morning after a heavy week.", ics: false },
  ],
};

// ---------- Weekly report  (GET /api/report?week=…) ----------

export const report = {
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
  moodThis: ["pleasant", "pleasant", "neutral", "unpleasant", "pleasant", "pleasant", "pleasant"] as ("pleasant" | "neutral" | "unpleasant")[],
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

// ---------- Ask  (POST /api/chat) ----------

export type TraceStep = { tool: string; seconds: number; summary: string; critic?: boolean };

export const sampleRun = {
  id: 212,
  question: "How's my week looking?",
  steps: 7,
  seconds: 3.9,
  answerIntro: "Mostly fine, with one rough spot. Here's your predicted readiness for each day:",
  answerOutro:
    "Thursday is the risk: 8h booked right after a late Wednesday. On similar days your readiness dropped about 1.8 points (n = 21). That's a pattern, not a guarantee. Moving Wednesday's late study block earlier is the easiest fix, and you're free 4:00–5:30 that day.",
  suggestion: { title: "Study block · Wed Nov 18, 4:00–5:30 PM", file: "study-wed-nov18.ics" },
  trace: [
    { tool: "get_calendar", seconds: 0.2, summary: "Nov 16–22 → 23 events · 34h booked" },
    { tool: "query_data", seconds: 0.3, summary: "readiness, sleep · last 90 days" },
    { tool: "forecast_week", seconds: 0.6, summary: "Thu readiness 4/10 · 21 similar days" },
    { tool: "compute_correlation", seconds: 0.3, summary: "late events → sleep · r = −0.41 · n = 17" },
    { tool: "find_free_time", seconds: 0.1, summary: "Wed 4:00–5:30 PM free" },
    { tool: "make_ics_event", seconds: 0.1, summary: "study-wed-nov18.ics" },
    { tool: "critic", seconds: 0.7, summary: "6/6 numbers traced · wording kept correlational", critic: true },
  ] as TraceStep[],
};

export const recentChats = ["How's my week looking?", "Why was Thursday rough?", "Does gym help my mood?"];

export const suggestedQuestions = ["How's my week looking?", "Why was last week better?", "When should I work out this week?"];
