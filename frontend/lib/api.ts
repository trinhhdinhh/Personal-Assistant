
import type { Report } from "@/lib/mock-data";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function getReport(): Promise<Report> {
  const res = await fetch(`${BACKEND}/api/report`);
  if (!res.ok) throw new Error(`report failed: ${res.status}`);
  return res.json();
}
