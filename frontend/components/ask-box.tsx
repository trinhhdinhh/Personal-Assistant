"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { suggestedQuestions } from "@/lib/mock-data";

/** Quick-ask box on the Brief page. Sends the question to /ask. */
export function AskBox() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function go(question: string) {
    const text = question.trim();
    router.push(text ? `/ask?q=${encodeURIComponent(text)}` : "/ask");
  }

  return (
    <section className="bg-card border-primary/35 flex flex-col gap-3 rounded-xl border p-4">
      <label htmlFor="ask" className="hud-label text-primary">Ask your agent</label>
      <form
        className="flex gap-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          go(q);
        }}
      >
        <Input
          id="ask"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Why was last week so unproductive?"
          className="h-12 text-[15px]"
        />
        <Button type="submit" className="h-12 px-5">Send</Button>
      </form>
      <div className="flex flex-wrap gap-2">
        {suggestedQuestions.map((s) => (
          <Button
            key={s}
            type="button"
            variant="outline"
            size="sm"
            className="text-muted-foreground h-9 rounded-full bg-transparent"
            onClick={() => go(s)}
          >
            {s}
          </Button>
        ))}
      </div>
    </section>
  );
}
