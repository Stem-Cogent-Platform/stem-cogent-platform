import { Suspense } from "react";

import { AuthExperience } from "@/components/auth-experience";

export default function SignupPage() {
  return <Suspense fallback={<main className="centered-state">Preparing your workspace…</main>}><AuthExperience mode="signup" /></Suspense>;
}
