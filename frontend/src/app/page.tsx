import { Suspense } from "react";

import { AuthExperience } from "@/components/auth-experience";

export default function HomePage() {
  return <Suspense fallback={<main className="centered-state">Preparing Stem Cogent…</main>}><AuthExperience mode="signup" /></Suspense>;
}
