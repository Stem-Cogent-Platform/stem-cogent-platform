"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, ReactNode, useEffect, useState } from "react";

import { StemMark } from "@/components/stem-mark";
import { apiRequest, bootstrapSession, currentUser, logout } from "@/lib/api";

const navigation = [
  ["/briefing", "My Decision Briefing", "briefing"],
  ["/company", "Company Lens", "company"],
  ["/watchlist", "Watchlist", "watch"],
  ["/intelligence", "Wider Intelligence", "intelligence"],
  ["/alerts", "Alerts", "alerts"],
  ["/digests", "Digests", "digests"]
] as const;

type ShellAlert = {
  id: string;
  brief_id: string;
  priority: string;
  subject: string;
  read_at?: string | null;
  payload?: { why_delivered?: string };
};

function NavIcon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    briefing: <><path d="M4 5.5h16M4 12h10M4 18.5h13" /><circle cx="18" cy="12" r="2" /></>,
    company: <><path d="M4 21V7l8-4 8 4v14M8 9h1m6 0h1M8 13h1m6 0h1M9 21v-4h6v4" /></>,
    watch: <><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" /><circle cx="12" cy="12" r="2.5" /></>,
    intelligence: <><path d="M4 19V9m5 10V5m5 14v-7m5 7V3" /></>,
    alerts: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    digests: <><path d="M5 3h11l3 3v15H5zM8 9h8M8 13h8M8 17h5" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></>
  };
  return <svg aria-hidden="true" className="nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7">{paths[name]}</svg>;
}

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [user, setUser] = useState<Record<string, unknown>>({});
  const [query, setQuery] = useState("");
  const [alerts, setAlerts] = useState<ShellAlert[]>([]);

  useEffect(() => {
    let active = true;
    void bootstrapSession().then((authenticated) => {
      if (!active) return;
      if (!authenticated) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }
      setUser(currentUser() ?? {});
      setReady(true);
      void apiRequest<ShellAlert[]>("/api/v1/alerts")
        .then((alerts) => {
          if (active) setAlerts(alerts);
        })
        .catch(() => undefined);
    });
    return () => { active = false; };
  }, [pathname, router]);

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    if (normalized.length >= 2) router.push(`/search?q=${encodeURIComponent(normalized)}`);
  }

  async function openAlert(alert: ShellAlert) {
    if (!alert.read_at) {
      await apiRequest(`/api/v1/alerts/${alert.id}/read`, { method: "POST" });
      setAlerts((items) => items.map((item) => item.id === alert.id ? { ...item, read_at: new Date().toISOString() } : item));
    }
    setNotificationsOpen(false);
    router.push(`/briefs/${alert.brief_id}`);
  }

  if (!ready) return <main className="centered-state"><p>Opening your workspace…</p></main>;

  const displayName = String(user.display_name ?? "Stem user");
  const workspaceName = String(user.workspace_name ?? "Workspace");
  const permissionLabel = user.permission_role === "ADMIN" ? "Workspace owner" : String(user.permission_role ?? "Member").replaceAll("_", " ");
  const unreadAlerts = alerts.filter((alert) => !alert.read_at).length;
  const initials = displayName.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();

  return (
    <main className={sidebarCollapsed ? "app-shell sidebar-collapsed" : "app-shell"}>
      {mobileOpen && <button aria-label="Close navigation" className="sidebar-scrim" onClick={() => setMobileOpen(false)} type="button" />}
      <aside className={mobileOpen ? "app-sidebar mobile-open" : "app-sidebar"}>
        <Link className="sidebar-brand" href="/briefing"><StemMark compact /><span>Stem Cogent</span></Link>
        <button aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"} className="sidebar-collapse" onClick={() => setSidebarCollapsed((value) => !value)} type="button">{sidebarCollapsed ? "›" : "‹"}</button>
        <div className="sidebar-section-label">Workspace</div>
        <nav aria-label="Primary navigation">
          {navigation.map(([href, text, icon]) => {
            const active = pathname.startsWith(href);
            return <Link aria-current={active ? "page" : undefined} className={active ? "active" : ""} href={href} key={href} onClick={() => setMobileOpen(false)}><NavIcon name={icon} /><span>{text}</span>{href === "/alerts" && unreadAlerts > 0 && <i className="nav-count">{unreadAlerts > 99 ? "99+" : unreadAlerts}</i>}</Link>;
          })}
        </nav>
        <div className="sidebar-spacer" />
        <nav aria-label="Account navigation">
          <Link className={pathname.startsWith("/settings") ? "active" : ""} href="/settings"><NavIcon name="settings" /><span>Settings</span></Link>
        </nav>
        <div className="sidebar-user">
          <span className="user-avatar">{initials || "SC"}</span>
          <div><strong>{displayName}</strong><small>{permissionLabel}</small></div>
          <button aria-label="Sign out" onClick={() => void signOut()} type="button">↗</button>
        </div>
      </aside>
      <div className="app-frame">
        <header className="app-topnav">
          <button aria-label="Open navigation" className="mobile-menu" onClick={() => setMobileOpen(true)} type="button">☰</button>
          <form className="global-search" onSubmit={search} role="search"><span aria-hidden="true">⌕</span><input aria-label="Search briefs, intelligence, and entities" onChange={(event) => setQuery(event.target.value)} placeholder="Search briefs, intelligence, entities…" type="search" value={query} /><button className="sr-only" type="submit">Search</button></form>
          <div className="topnav-actions">
            <button aria-expanded={notificationsOpen} aria-label={unreadAlerts ? `View ${unreadAlerts} unread alerts` : "View alerts"} className="topnav-icon" onClick={() => setNotificationsOpen((value) => !value)} type="button"><NavIcon name="alerts" />{unreadAlerts > 0 && <i />}</button>
            <span className="company-switcher"><small>Company</small><strong>{workspaceName}</strong></span>
            <span className="user-avatar compact">{initials || "SC"}</span>
          </div>
        </header>
        <div className="app-content">{children}</div>
      </div>
      {notificationsOpen && <>
        <button aria-label="Close notifications" className="notification-scrim" onClick={() => setNotificationsOpen(false)} type="button" />
        <aside aria-label="Notifications" className="notification-drawer">
          <header><div><p className="eyebrow">Live workspace</p><h2>Notifications</h2></div><button aria-label="Close notifications" onClick={() => setNotificationsOpen(false)} type="button">×</button></header>
          <div className="notification-stack">{alerts.slice(0, 8).map((alert) => <button className={alert.read_at ? "" : "unread"} key={alert.id} onClick={() => void openAlert(alert)} type="button"><span className={`priority-chip priority-${alert.priority.toLowerCase()}`}>{alert.priority}</span><strong>{alert.subject}</strong><small>{alert.payload?.why_delivered || "Matched your configured Decision Lens."}</small></button>)}{alerts.length === 0 && <p>No notifications yet. New evidence-backed alerts will appear here.</p>}</div>
          <Link href="/alerts" onClick={() => setNotificationsOpen(false)}>View alert history →</Link>
        </aside>
      </>}
    </main>
  );
}
