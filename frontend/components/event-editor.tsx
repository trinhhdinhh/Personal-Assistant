"use client";

import { useEffect, useState } from "react";
import { Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { deleteEvent, saveEvent, type Category, type EventInput } from "@/lib/api";

/**
 * The add / edit form for one event on the Week calendar.
 * This is you changing your own schedule; the agent never edits it.
 */

export const CATEGORIES: { value: Category; label: string }[] = [
  { value: "class", label: "Class" },
  { value: "study", label: "Study" },
  { value: "work", label: "Work" },
  { value: "gym", label: "Gym" },
  { value: "social", label: "Social" },
  { value: "other", label: "Other" },
];

export type Draft = EventInput & { id: number | null };

const selectClass =
  "border-input bg-background h-11 w-full rounded-md border px-3 text-base outline-none md:text-sm focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]";

export function EventEditor({
  draft,
  days,
  onClose,
  onSaved,
}: {
  draft: Draft;
  days: { iso: string; label: string }[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Draft>(draft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editing = draft.id !== null;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setBusy(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const { id, ...event } = form;
    run(() => saveEvent(id, event));
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-editor-title"
        onSubmit={submit}
        className="bg-card flex w-full max-w-md flex-col gap-4 rounded-xl border p-5 shadow-2xl"
      >
        <div className="flex items-center justify-between">
          <h2 id="event-editor-title" className="text-lg font-semibold">
            {editing ? "Edit event" : "Add event"}
          </h2>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X />
          </Button>
        </div>

        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-muted-foreground">Title</span>
          <Input autoFocus required maxLength={200} value={form.title} onChange={(e) => set("title", e.target.value)} />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-muted-foreground">Day</span>
            <select className={selectClass} value={form.date} onChange={(e) => set("date", e.target.value)}>
              {days.map((d) => (
                <option key={d.iso} value={d.iso}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-muted-foreground">Type</span>
            <select
              className={selectClass}
              value={form.category}
              onChange={(e) => set("category", e.target.value as Category)}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-muted-foreground">Starts</span>
            <Input type="time" step={300} required value={form.start} onChange={(e) => set("start", e.target.value)} />
          </label>
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="text-muted-foreground">Ends</span>
            <Input type="time" step={300} required value={form.end} onChange={(e) => set("end", e.target.value)} />
          </label>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="flex items-center gap-2">
          {editing && (
            <Button
              type="button"
              variant="ghost"
              className="text-destructive hover:text-destructive mr-auto"
              disabled={busy}
              onClick={() => run(() => deleteEvent(draft.id!))}
            >
              <Trash2 /> Delete
            </Button>
          )}
          <Button type="button" variant="outline" className="ml-auto" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
        <p className="text-muted-foreground text-xs">
          Saved in Life Agent only. The forecast updates right away; your iCloud calendar isn&apos;t changed.
        </p>
      </form>
    </div>
  );
}
