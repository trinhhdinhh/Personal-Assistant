import { Suspense } from "react";

import { Chat } from "@/components/chat";

export default function AskPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground font-mono text-sm">Loading agent…</p>}>
      <Chat />
    </Suspense>
  );
}
