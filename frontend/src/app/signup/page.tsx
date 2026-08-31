import { Suspense } from "react";
import { redirect } from "next/navigation";

import { AuthExperience } from "@/components/auth-experience";

export default function SignupPage() {
  if (process.env.NEXT_PUBLIC_PHASE5_PILOT_INVITES_ENABLED === "true") redirect("/login");
  return <Suspense fallback={<main className="centered-state">Preparing your workspace…</main>}><AuthExperience mode="signup" /></Suspense>;
}
