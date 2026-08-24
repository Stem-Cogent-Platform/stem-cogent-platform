"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { StemMark } from "@/components/stem-mark";
import { login } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await login({
        workspace_id: String(form.get("workspace")),
        email: String(form.get("email")),
        password: String(form.get("password"))
      });
      const destination = search.get("next");
      router.replace(destination?.startsWith("/") && !destination.startsWith("//") ? destination : "/");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "We could not sign you in. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <Link className="wordmark" href="/"><StemMark /><span>Stem</span></Link>
        <p className="eyebrow">Invite-only pilot access</p>
        <h1>Decision intelligence with evidence in view.</h1>
        <p>Sign in with the workspace ID supplied in your pilot welcome pack. Stem never asks for payment details on this page.</p>
      </section>
      <form className="auth-card" onSubmit={submit}>
        <p className="eyebrow">Secure sign in</p>
        <h2>Open your workspace</h2>
        <label><span>Workspace ID</span><input autoComplete="organization" name="workspace" pattern="[0-9a-fA-F-]{36}" required /></label>
        <label><span>Work email</span><input autoComplete="email" name="email" type="email" required /></label>
        <label><span>Password</span><input autoComplete="current-password" minLength={12} name="password" type="password" required /></label>
        {message && <p className="form-message" role="status">{message}</p>}
        <button className="primary-button" disabled={saving} type="submit">{saving ? "Signing in…" : "Sign in"}</button>
        <small>Access is limited to invited pilot participants. Contact your Stem pilot lead if your credentials have not arrived.</small>
      </form>
    </main>
  );
}

export default function LoginPage() {
  return <Suspense fallback={<main className="auth-page"><p>Preparing secure sign in…</p></main>}><LoginForm /></Suspense>;
}
