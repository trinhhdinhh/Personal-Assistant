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
| `app/page.tsx` | 01 Brief (dashboard + daily brief) |
| `app/ask/` | 02 Ask (agent chat + tool trace + approval card) |
| `app/know/` | 03 Know (stats, scatter, downfalls, correlations) |
| `app/plan/` | 04 Plan (week grid, focus windows) |
| `app/learn/` | 05 Learn (n-of-1 experiments) |
| `components/ui/` | shadcn components (add more with `npx shadcn@latest add <name>`) |
| `components/hud.tsx` | HUD pieces: logo mark, corner brackets, readiness ring, day strip |
| `components/app-shell.tsx` | Sidebar + layout |
| `lib/mock-data.ts` | **All data** — synthetic, shaped like the future API responses |
| `app/globals.css` | Theme: shadcn tokens + `--success` / `--warning` |

## Connecting the backend

Every page reads from `lib/mock-data.ts`. Each export is commented with the
Django endpoint it stands in for (e.g. `brief` → `GET /api/brief`). Swap one
export at a time for a `fetch` to that endpoint and keep the same TypeScript type.
