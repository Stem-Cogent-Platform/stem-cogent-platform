import { Suspense } from "react";

import { AuthExperience } from "@/components/auth-experience";

export default function LoginPage() {
  return <Suspense fallback={<main className="centered-state">Preparing secure sign in…</main>}><AuthExperience mode="login" /></Suspense>;
}
