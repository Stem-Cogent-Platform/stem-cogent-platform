import { Suspense } from "react";
import { redirect } from "next/navigation";
import { EnterpriseAuthCard } from "@/components/enterprise-auth-card";

export default function HomePage() {
  if (process.env.NEXT_PUBLIC_PHASE5_PILOT_INVITES_ENABLED === "true") redirect("/login");
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-50 flex items-center justify-center text-sm text-slate-500">Preparing Stem Cogent…</main>}>
      <EnterpriseAuthCard initialMode="signup" />
    </Suspense>
  );
}
