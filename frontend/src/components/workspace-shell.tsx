"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { clearSession, logout } from "@/lib/api";
import { StemMark } from "@/components/stem-mark";

const navigation = [
  ["/briefing", "My Briefing"],
  ["/company", "Company Lens"],
  ["/watchlist", "Watchlist"],
  ["/intelligence", "Intelligence"],
  ["/alerts", "Alerts"],
  ["/digests", "Digests"],
  ["/pilot", "Guided Pilot"]
] as const;

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [label, setLabel] = useState("Workspace");

  useEffect(() => {
    const token = window.sessionStorage.getItem("sc_access_token");
    if (!token) {
      clearSession();
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    const labelTimer = window.setTimeout(() => {
      try {
        const user = JSON.parse(window.sessionStorage.getItem("sc_user") ?? "{}");
        setLabel(user.workspace_name ?? user.display_name ?? "Workspace");
      } catch {
        setLabel("Workspace");
      }
    }, 0);
    return () => window.clearTimeout(labelTimer);
  }, [pathname, router]);

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  return (
    <main className="workspace-page">
      <header className="workspace-header">
        <Link className="wordmark" href="/briefing" aria-label="Stem briefing">
          <StemMark compact />
          <span>Stem</span>
        </Link>
        <nav aria-label="Primary">
          {navigation.map(([href, text]) => (
            <Link className={pathname.startsWith(href) ? "active" : ""} href={href} key={href}>
              {text}
            </Link>
          ))}
        </nav>
        <div className="workspace-account">
          <span className="profile-chip">{label}</span>
          <Link className="text-link" href="/settings/billing">Billing</Link>
          <button className="link-button" onClick={() => void signOut()} type="button">Sign out</button>
        </div>
      </header>
      {children}
    </main>
  );
}
