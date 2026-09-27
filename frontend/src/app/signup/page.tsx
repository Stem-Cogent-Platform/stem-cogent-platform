import { Suspense } from "react";
import { EnterpriseAuthCard } from "@/components/enterprise-auth-card";

export default function SignupPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-50 flex items-center justify-center text-sm text-slate-500">Preparing workspace registration…</main>}>
      <EnterpriseAuthCard initialMode="signup" />
    </Suspense>
  );
}
