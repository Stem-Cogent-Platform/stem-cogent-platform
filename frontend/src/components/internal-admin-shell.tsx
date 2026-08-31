"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { StemMark } from "@/components/stem-mark";
import { bootstrapSession, currentUser, logout } from "@/lib/api";

const navigation = [["/internal/admin/tenants", "Pilot tenants"], ["/internal/admin/entity-review", "Entity review"], ["/internal/admin/pipeline", "Pipeline"]] as const;

export function InternalAdminShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let active = true;
    void bootstrapSession().then((authenticated) => {
      if (!active) return;
      if (!authenticated || currentUser()?.permission_role !== "SYSTEM_ADMIN") router.replace(`/internal/login?next=${encodeURIComponent(pathname)}`);
      else setReady(true);
    });
    return () => { active = false; };
  }, [pathname, router]);
  if (!ready) return <main aria-busy="true" className="centered-state">Securing the operator workspace...</main>;
  return <main className="internal-shell"><aside><Link className="sidebar-brand" href="/internal/admin/tenants"><StemMark compact /><span>Stem Operator</span></Link><p>Internal · MFA protected</p><nav>{navigation.map(([href, label]) => <Link aria-current={pathname.startsWith(href) ? "page" : undefined} className={pathname.startsWith(href) ? "active" : ""} href={href} key={href}>{label}</Link>)}</nav><button onClick={() => void logout().then(() => router.replace("/internal/login"))} type="button">Sign out</button></aside><div className="internal-content">{children}</div></main>;
}
