"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { bootstrapSession } from "@/lib/api";

function Callback() {
  const router = useRouter();
  const search = useSearchParams();
  const [message, setMessage] = useState("Completing secure sign in…");
  useEffect(() => {
    void bootstrapSession().then((authenticated) => {
      if (!authenticated) {
        setMessage("We could not complete single sign-on. Return to sign in and try again.");
        return;
      }
      router.replace(search.get("new") === "1" ? "/onboarding/legal" : "/briefing");
    });
  }, [router, search]);
  return <main className="centered-state"><section className="state-card"><p className="eyebrow">Secure authentication</p><h1>{message}</h1></section></main>;
}

export default function AuthCallbackPage() {
  return <Suspense fallback={<main className="centered-state">Completing secure sign in…</main>}><Callback /></Suspense>;
}
