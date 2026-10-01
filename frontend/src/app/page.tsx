import { Suspense } from "react";
import AuthLayout from "./(auth)/layout";
import SignupPage from "./(auth)/signup/page";

export default function HomePage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-50 flex items-center justify-center text-sm text-slate-500">Preparing Stem Cogent…</main>}>
      <AuthLayout>
        <SignupPage />
      </AuthLayout>
    </Suspense>
  );
}
