"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { agentStatus } from "@/lib/mock-data";
import { CoreMark } from "@/components/hud";

const NAV = [
  { href: "/", num: "01", label: "Brief" },
  { href: "/ask", num: "02", label: "Ask" },
  { href: "/know", num: "03", label: "Know" },
  { href: "/plan", num: "04", label: "Plan" },
  { href: "/learn", num: "05", label: "Learn" },
] as const;

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="bg-sidebar border-sidebar-border flex shrink-0 flex-col gap-6 border-b px-4 py-5 md:sticky md:top-0 md:h-screen md:w-60 md:border-r md:border-b-0 md:py-6">
        <Link href="/" className="flex items-center gap-3 px-2 text-foreground no-underline">
          <CoreMark className="size-9" />
          <span className="flex flex-col gap-0.5">
            <span className="text-[15px] font-bold tracking-[0.2em]">LIFE AGENT</span>
            <span className="text-muted-foreground font-mono text-[11px]">v0.1 · mock data</span>
          </span>
        </Link>

        <nav aria-label="Primary" className="flex gap-1 overflow-x-auto md:flex-col">
          {NAV.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-11 shrink-0 items-center gap-3 rounded-lg border px-3 text-sm transition-colors",
                  active
                    ? "border-primary/35 bg-primary/10 text-primary font-semibold"
                    : "text-foreground hover:bg-sidebar-accent border-transparent",
                )}
              >
                <span className={cn("font-mono text-[11px]", !active && "text-muted-foreground")}>
                  {item.num}
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="bg-card text-muted-foreground mt-auto hidden flex-col gap-2.5 rounded-lg border p-3.5 font-mono text-[11px] md:flex">
          <div className="text-success flex items-center gap-2">
            <span className="bg-success size-2 rounded-full" aria-hidden="true" />
            AGENT {agentStatus.online ? "ONLINE" : "OFFLINE"}
          </div>
          <div className="flex justify-between">
            <span>tools</span>
            <span className="text-foreground">{agentStatus.tools}</span>
          </div>
          <div className="flex justify-between">
            <span>critic</span>
            <span className="text-foreground">{agentStatus.critic ? "enabled" : "off"}</span>
          </div>
          <div className="flex justify-between">
            <span>last sync</span>
            <span className="text-foreground">{agentStatus.lastSync}</span>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 md:px-10 md:py-8">{children}</main>
    </div>
  );
}
