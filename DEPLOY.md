# Deploying the Life Agent and connecting it to Claude

After this, you can open Claude on the web, desktop or phone and ask *"how's my week looking?"*. Your own agent answers, with its steps and checks.

```
Claude ──OAuth sign-in──▶ Render web service (uvicorn config.asgi:app)
                            ├─ /mcp            the connector (agent/mcp_server.py)
                            ├─ /o/authorize    sign-in (django-oauth-toolkit)
                            └─ /admin/login    your Django login
                          Render Postgres · OpenRouter (the agent's model)
```

The server runs on **synthetic data** (`DEMO_TODAY=2026-11-16`) until real Apple Watch and calendar ingest is added.

## 1. Create the service on Render (about 10 minutes)

1. Push this branch to GitHub.
2. Render → **New → Blueprint** → pick the repo. Render reads `render.yaml` and creates:
   - `life-agent-db`, a Postgres database
   - `life-agent`, a Starter web service that's always on. The free plan sleeps, and Claude may time out waking it.
3. When it asks for **`OPENROUTER_API_KEY`**, paste your school key. It only lives in Render's dashboard, never in git.
4. Wait for the deploy to finish, then open `https://<your-service>.onrender.com/healthz`. You should see `{"ok": true}`.
   Render sets the public address automatically (`RENDER_EXTERNAL_HOSTNAME`). If you add a custom domain later, set `PUBLIC_URL` to it.

## 2. One-time setup (Render → your service → **Shell**)

```bash
python manage.py seed_synthetic           # 60 days of fake history + this week's calendar
python manage.py seed_demo_suggestions    # three past suggestions, so follow-ups show up
python manage.py createsuperuser          # YOUR login for connecting Claude (pick a strong password)
python manage.py create_claude_client     # prints the Client ID and Client secret ONCE
```

Copy the client ID and secret straight into Claude in the next step. Don't save them anywhere else. If you lose the secret, run `create_claude_client` again, which replaces the old one.

## 3. Connect it in Claude

1. Claude → **Settings → Connectors → Add custom connector**.
2. Fill in:
   - **Name:** Life Agent
   - **URL:** `https://<your-service>.onrender.com/mcp`
   - **Authentication:** OAuth → **Use your own OAuth client**. Paste the client ID and secret.
3. Click **Connect**. You'll land on your Django login: sign in, then click **Authorize**. You're sent back to Claude.
4. Try it:
   - *"Use Life Agent: how's my week looking?"* runs `ask_agent` and should show the agent's answer, steps and checks.
   - *"Show my Life Agent weekly report"* runs `get_weekly_report`.
   - *"What's on my Life Agent brief today?"* runs `get_today_brief`.
5. Open the Claude app on your phone with the same account and try one question there too.

## What the connector can and can't do

| Tool | What it does |
|---|---|
| `get_today_brief` | readiness, today's schedule, suggestions with calendar files |
| `get_week_forecast` | 7-day forecast, risks, the patterns behind them |
| `get_weekly_report` | this week vs last, plus follow-ups on past suggestions |
| `get_recent_trends` | recent averages vs the period before |
| `ask_agent` | runs **this project's agent** (read-only, max 6 steps, 40 questions a day) |

- **Read-only:** the agent can't save suggestions or change anything through Claude, and nothing touches your calendar.
- **Summaries only:** daily summaries, never raw samples or mood entries.
- **Login required:** every request needs a token. Only staff accounts (you) can sign in. Tokens last 1 hour and Claude refreshes them for 30 days.
- **The local JSON API (`/api/...`) is off** on the server (`API_ENABLED=false`). The Next.js pages are for local use.

## Checks after a deploy

```bash
curl https://<service>.onrender.com/healthz                                      # {"ok": true}
curl https://<service>.onrender.com/.well-known/oauth-protected-resource/mcp     # resource + issuer
curl -i -X POST https://<service>.onrender.com/mcp                               # 401 + WWW-Authenticate
curl -i https://<service>.onrender.com/api/report                                # 404 (API off)
```

## Troubleshooting

- **The connector says it can't reach the server:** check that `/healthz` works and the service is on the Starter plan, not sleeping.
- **Sign-in loops or "invalid redirect":** run `create_claude_client` again and re-enter the new ID and secret in Claude.
- **"The daily limit … is used up":** raise `MCP_DAILY_ASK_LIMIT` in Render's environment if you need more.
- **Slow or cut-off answers:** set `AGENT_MODEL=anthropic/claude-sonnet-5.5` for faster runs, or lower `MCP_AGENT_MAX_STEPS`.
- **Rotating secrets:** `DJANGO_SECRET_KEY` (regenerate it in Render), the OpenRouter key (in Render's env), the Claude client (`create_claude_client`).

## Running the server like production, locally

```bash
cd backend
../.venv/bin/uvicorn config.asgi:app --port 8000   # Django + /mcp in one process
```

Locally `/mcp` still needs a token. The tests in `agent/tests/test_mcp.py` run the whole sign-in and MCP calls without any network.
