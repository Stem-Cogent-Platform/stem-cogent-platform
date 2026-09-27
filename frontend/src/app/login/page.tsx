import { Suspense } from "react";
import { EnterpriseAuthCard } from "@/components/enterprise-auth-card";

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-50 flex items-center justify-center text-sm text-slate-500">Preparing secure sign in…</main>}>
      <EnterpriseAuthCard initialMode="login" />
    </Suspense>
  );
}
