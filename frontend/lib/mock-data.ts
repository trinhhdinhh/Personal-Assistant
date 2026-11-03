/**
 * Mock data for the UI while the Django backend is being built.
 *
 * Every export here mirrors what a backend endpoint will return
 * (see CLAUDE.md). To go live, replace one export at a time with a
 * fetch to the matching endpoint, keeping the same TypeScript shape.
 *
 * All values are synthetic. Never put real personal data in this file.
 */

// ---------- Shared ----------

export type Tone = "primary" | "success" | "warning" | "destructive" | "muted";

export const agentStatus = {
  online: true,
  tools: 19,
  critic: true,
  lastSync: "07:58",
};

// ---------- Brief  (GET /api/brief) ----------

export const brief = {
  dateLabel: "WED · OCT 28 · 08:00 CDT",
  greetingName: "Trinh",
  readiness: { score: 72, energyForecast: 3, sleep: "6h 41m", deadlines: 2 },
  critic: { passed: true, toolCalls: 6 },
  sections: [
    {
      key: "yesterday",
      label: "01 · Yesterday",
      body: "Hit 2 of 3 intentions. Missed: LeetCode set. Blocker: “phone after 11pm”.",
    },
    {
      key: "pattern",
      label: "02 · Pattern",
      body: "Focus averages 1.1 pts lower after nights under 6h.",
      evidence: "n=41 days",
    },
    {
      key: "today",
      label: "03 · Today",
      body: "Report due 11:59 PM. Best focus window: 9:30–11:30, already blocked for it.",
    },
    {
      key: "differently",
      label: "04 · Do differently",
      body: "Phone on the charger by 11pm tonight. Day 9 of 14 in your experiment.",
      highlight: true,
    },
  ],
};

// ---------- Goals  (GET /api/goals) ----------

export type GoalProgress = {
  id: number;
  title: string;
  current: number;
  target: number;
  unit?: string;
  onTrack: boolean;
};

export const goals: GoalProgress[] = [
  { id: 1, title: "Sleep 7h avg", current: 6.6, target: 7, unit: "h", onTrack: false },
  { id: 2, title: "Gym sessions", current: 3, target: 4, onTrack: true },
  { id: 3, title: "LeetCode problems", current: 4, target: 10, onTrack: false },
  { id: 4, title: "Submit 24h early", current: 1, target: 1, onTrack: true },
];

// ---------- Today timeline  (GET /api/calendar?date=today) ----------

export type TimelineItem = {
  time: string;
  title: string;
  meta: string;
  kind: "suggested" | "fixed" | "goal" | "deadline";
};

export const today: TimelineItem[] = [
  { time: "09:30", title: "Focus block · ML report", meta: "suggested · best window", kind: "suggested" },
  { time: "12:00", title: "Class", meta: "fixed · 75 min", kind: "fixed" },
  { time: "14:00", title: "Work shift", meta: "fixed · 3h", kind: "fixed" },
  { time: "17:30", title: "Gym", meta: "goal · 4th session", kind: "goal" },
  { time: "23:59", title: "Deadline · ML report", meta: "you usually submit within 3h of deadlines", kind: "deadline" },
];

// ---------- Experiments  (GET /api/experiments) ----------

export type DayStatus = "kept" | "missed" | "pending" | "today";

export const activeExperiment = {
  id: 7,
  day: 9,
  durationDays: 14,
  startedLabel: "started Oct 20 · proposed by agent",
  hypothesis: "Phone on the charger by 11pm raises next-morning intention completion.",
  shortHypothesis: "No phone after 11pm → does morning intention completion go up?",
  intervention: "No phone after 11pm",
  metric: "Intentions hit (next day)",
  trackedBy: "App-open log",
  days: [
    "kept", "kept", "missed", "kept", "kept", "kept", "missed", "kept", "kept",
    "today", "pending", "pending", "pending", "pending",
  ] as DayStatus[],
  baselinePct: 58,
  interventionPct: 76,
  pValue: 0.21,
};

export const completedExperiments = [
  {
    id: 4,
    title: "Study at the library",
    result: "WORKED",
    tone: "success" as Tone,
    detail: "+21 pts intention completion · p = 0.03 · n = 14",
    learned: "saved: prefer library for deep work",
  },
  {
    id: 5,
    title: "No caffeine after 2pm",
    result: "NO EFFECT",
    tone: "muted" as Tone,
    detail: "+4 min sleep · p = 0.71 · n = 14",
    learned: "no change to model",
  },
  {
    id: 6,
    title: "Morning gym vs evening",
    result: "WORSE",
    tone: "warning" as Tone,
    detail: "−0.6 focus on class days · p = 0.04 · n = 14",
    learned: "saved: schedule gym after 5pm",
  },
];

export const proposedExperiments = [
  {
    id: 8,
    title: "Start assignments 48h before the deadline",
    why: "14 of 20 submissions landed in the last 3h. Metric: grade + stress check-in. 3 assignments.",
  },
  {
    id: 9,
    title: "7h sleep floor on weeknights",
    why: "Focus is 1.1 pts lower after short nights (n = 41). Metric: next-day focus. 14 days.",
  },
];

// ---------- Know  (GET /api/insights?range=…) ----------

export type Range = "7d" | "30d" | "90d";

export type Stat = { label: string; value: string; suffix?: string; delta: string; tone: Tone };

export const statsByRange: Record<Range, Stat[]> = {
  "7d": [
    { label: "Avg sleep", value: "6h 21m", delta: "▼ 31m vs prior 7d", tone: "warning" },
    { label: "Intentions hit", value: "44%", delta: "▼ 34 pts", tone: "destructive" },
    { label: "Avg focus", value: "2.9", suffix: "/5", delta: "▼ 0.6", tone: "warning" },
    { label: "Last-minute submits", value: "2/2", delta: "within 3h of deadline", tone: "warning" },
  ],
  "30d": [
    { label: "Avg sleep", value: "6h 39m", delta: "▼ 9m vs prior 30d", tone: "warning" },
    { label: "Intentions hit", value: "61%", delta: "▲ 3 pts", tone: "success" },
    { label: "Avg focus", value: "3.3", suffix: "/5", delta: "— flat", tone: "muted" },
    { label: "Last-minute submits", value: "67%", delta: "within 3h of deadline", tone: "warning" },
  ],
  "90d": [
    { label: "Avg sleep", value: "6h 48m", delta: "▼ 14m vs prior 90d", tone: "warning" },
    { label: "Intentions hit", value: "64%", delta: "▲ 6 pts", tone: "success" },
    { label: "Avg focus", value: "3.4", suffix: "/5", delta: "— flat", tone: "muted" },
    { label: "Last-minute submits", value: "70%", delta: "within 3h of deadline", tone: "warning" },
  ],
};

/** Sleep hours vs next-day focus (1–5), one point per day. */
export const sleepFocus: { sleep: number; focus: number }[] = [
  [4.3, 1.7], [4.6, 2.1], [4.9, 1.5], [5.1, 2.3], [5.4, 1.9], [5.6, 2.6], [5.7, 2.1],
  [6.1, 2.8], [6.3, 2.5], [6.6, 3.2], [6.8, 3.0], [7.0, 3.4], [7.2, 2.8], [7.4, 3.6],
  [7.5, 3.3], [7.7, 3.8], [7.9, 3.5], [8.1, 4.0], [8.3, 3.7], [8.4, 4.1], [8.6, 3.9],
  [8.7, 4.3], [8.9, 4.0], [9.0, 4.4], [6.4, 3.6], [7.1, 2.6], [5.9, 3.0], [8.0, 3.2],
].map(([sleep, focus]) => ({ sleep, focus }));

export const sleepFocusStats = { r: 0.52, n: 88 };

export const downfalls = [
  { title: "Late-night phone use", freq: "31 / 90 nights", detail: "Next morning: intentions hit 41% vs 74% otherwise.", tone: "destructive" as Tone },
  { title: "Last-minute submissions", freq: "14 / 20 assignments", detail: "Submitted within 3h of the deadline.", tone: "warning" as Tone },
  { title: "Skipped focus blocks", freq: "11 / 38 blocks", detail: "Mostly afternoon blocks scheduled after class.", tone: "warning" as Tone },
  { title: "Underestimated reading", freq: "1.6× estimate", detail: "From 23 timed sessions.", tone: "warning" as Tone },
];

export const correlations = [
  { input: "Sleep hours", outcome: "Focus", lag: "+1d", r: 0.52, n: 88, status: "test" },
  { input: "Late phone use", outcome: "Intentions hit", lag: "+1d", r: -0.48, n: 62, status: "testing" },
  { input: "Gym session", outcome: "Mood", lag: "+1d", r: 0.37, n: 90, status: "test" },
  { input: "Library visit", outcome: "Intentions hit", lag: "0d", r: 0.33, n: 90, status: "test" },
] as const;

// ---------- Plan  (GET /api/plan?week=…) ----------

export type BlockKind = "class" | "work" | "study" | "gym" | "social" | "suggested" | "skipped";

export type WeekBlock = {
  start: number; // hour, 24h (e.g. 9.5 = 9:30)
  end: number;
  title: string;
  kind: BlockKind;
};

export const week = {
  label: "OCT 26 – NOV 1",
  todayIndex: 2,
  feasibility: { feasible: true, solver: "OR-Tools", seconds: 0.4 },
  dayStart: 8,
  dayEnd: 22,
  days: [
    { label: "MON 26", blocks: [
      { start: 9, end: 10.4, title: "Class", kind: "class" },
      { start: 11, end: 13, title: "Study", kind: "study" },
      { start: 14, end: 17, title: "Work", kind: "work" },
      { start: 17.5, end: 18.75, title: "Gym ✓", kind: "gym" },
    ] },
    { label: "TUE 27", blocks: [
      { start: 9.5, end: 10.9, title: "Class", kind: "class" },
      { start: 11.5, end: 13.5, title: "Study · skipped", kind: "skipped" },
      { start: 14, end: 17, title: "Work", kind: "work" },
    ] },
    { label: "WED 28", deadlineAt: 23.9, blocks: [
      { start: 9.5, end: 11.5, title: "Focus · report", kind: "suggested" },
      { start: 12, end: 13.25, title: "Class", kind: "class" },
      { start: 14, end: 17, title: "Work", kind: "work" },
      { start: 17.5, end: 18.75, title: "Gym", kind: "gym" },
    ] },
    { label: "THU 29", blocks: [
      { start: 9.5, end: 11.5, title: "Focus", kind: "suggested" },
      { start: 12, end: 13.4, title: "Class", kind: "class" },
      { start: 14.5, end: 16.25, title: "Reading ×1.6", kind: "suggested" },
    ] },
    { label: "FRI 30", blocks: [
      { start: 9, end: 10.4, title: "Class", kind: "class" },
      { start: 14, end: 17, title: "Work", kind: "work" },
      { start: 17.5, end: 18.75, title: "Gym", kind: "gym" },
    ] },
    { label: "SAT 31", blocks: [
      { start: 9.5, end: 11.5, title: "LeetCode ×5", kind: "suggested" },
      { start: 18, end: 21, title: "Social", kind: "social" },
    ] },
    { label: "SUN 1", blocks: [
      { start: 11, end: 12.5, title: "Weekly review", kind: "study" },
    ] },
  ] as { label: string; deadlineAt?: number; blocks: WeekBlock[] }[],
};

export const toPlace = [
  { title: "ML report", estimate: "4h", adjusted: "5h" },
  { title: "Ch. 7 reading", estimate: "45m", adjusted: "72m" },
  { title: "LeetCode set", estimate: "6 problems" },
];

/** Average focus by 2-hour slot, 8am → 10pm (0–1). */
export const focusWindows = [0.35, 0.9, 0.8, 0.45, 0.2, 0.15, 0.3, 0.4];

// ---------- Ask  (POST /api/chat) ----------

export type TraceStep = { tool: string; seconds: number; summary: string; critic?: boolean };

export const sampleRun = {
  id: 142,
  question: "Why was last week so unproductive compared to the week before?",
  title: "Why was last week rough?",
  steps: 7,
  seconds: 4.8,
  answerIntro: "Intention completion fell from 78% to 44% week over week. Three things changed at the same time:",
  comparison: {
    periodA: "Oct 12–18",
    periodB: "Oct 19–25",
    rows: [
      { label: "Avg sleep", a: 0.92, b: 0.74, delta: "−1h 12m" },
      { label: "Late phone use", a: 0.28, b: 0.71, delta: "+2.5×" },
      { label: "Library visits", a: 0.8, b: 0.2, delta: "4 → 1" },
    ],
  },
  answerOutro:
    "The strongest link over your history is late phone use → missed morning intentions (r = −0.48, n = 62 days). That’s a correlation, not proof. Want to test it? I can protect your 9:30 focus block for the rest of this week.",
  approval: {
    tool: "create_event",
    count: 3,
    tier: "write_external",
    description: "Add “Focus · ML report” to iCloud Calendar, Thu–Sat 9:30–11:30.",
  },
  trace: [
    { tool: "evaluate_day", seconds: 0.2, summary: "range=14d → completion 78% / 44%" },
    { tool: "compare_periods", seconds: 0.4, summary: "sleep, app_opens, place_visits" },
    { tool: "detect_downfalls", seconds: 0.6, summary: "late_night_phone ×5 of 7" },
    { tool: "compute_correlation", seconds: 0.3, summary: "r=−0.48 · n=62 · lag=1d" },
    { tool: "generate_chart", seconds: 0.1, summary: "bar · week_over_week" },
    { tool: "check_feasibility", seconds: 0.4, summary: "OR-Tools · feasible" },
    { tool: "critic", seconds: 0.9, summary: "8/8 numbers traced · 1 claim softened (causal → correlational)", critic: true },
  ] as TraceStep[],
};

export const recentChats = ["Why was last week rough?", "Gym vs. next-day mood", "Plan finals week"];

export const suggestedQuestions = [
  "Does gym help my mood?",
  "Plan my week around the report",
  "What are my biggest downfalls?",
];
