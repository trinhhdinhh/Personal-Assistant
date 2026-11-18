// POST /api/chat: forwards the question to the Django agent and returns its answer.
// A route handler (not the /api rewrite) so long multi-step agent runs aren't cut off
// by the dev proxy's timeout, and so the backend address stays on the server.

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const body = await request.text();
  try {
    const res = await fetch(`${BACKEND}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: AbortSignal.timeout(180_000), // the agent makes several model calls
    });
    return new Response(await res.text(), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return Response.json(
      { error: "Couldn't reach the agent backend. Is the Django server running on port 8000?" },
      { status: 502 },
    );
  }
}
