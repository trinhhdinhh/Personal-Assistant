# Life Agent — frontend

Next.js (App Router) + TypeScript + Tailwind v4 + shadcn/ui, styled as a dark "Jarvis" HUD.

## Run it

```bash
cd frontend
npm install      # first time only
npm run dev      # http://localhost:3000
```

## Where things live

| Path | What |
|---|---|
| `app/page.tsx` | 01 Today (readiness, 3 suggestions, schedule with free gaps) |
| `app/week/` | 02 Week ahead (per-day forecast, why, suggested changes) |
| `app/report/` | 03 Weekly report (this week vs last, did my advice work?) |
| `app/ask/` | 04 Ask (agent chat + agent steps) |
| `components/ui/` | shadcn components (add more with `npx shadcn@latest add <name>`) |
| `components/hud.tsx` | HUD pieces: logo mark, corner brackets, readiness ring |
| `components/suggestion.tsx` | One suggestion with its evidence and an Add to calendar button |
| `components/sleep-chart.tsx` | Sleep per night, this week vs last |
| `components/app-shell.tsx` | Sidebar + layout |
| `lib/mock-data.ts` | **All data** — synthetic, shaped like the future API responses |
| `app/globals.css` | Theme: shadcn tokens + `--success` / `--warning` |

## Connecting the backend

Every page reads from `lib/mock-data.ts`. Each export is commented with the
Django endpoint it stands in for (e.g. `brief` → `GET /api/brief`). Swap one
export at a time for a `fetch` to that endpoint and keep the same TypeScript type.
