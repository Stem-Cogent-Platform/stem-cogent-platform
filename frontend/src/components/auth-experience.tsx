"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { StemMark } from "@/components/stem-mark";
import { ApiError, beginSso, login, register } from "@/lib/api";

export function AuthExperience({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const signup = mode === "signup";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      if (signup) {
        await register({
          company_name: String(form.get("company_name")),
          display_name: String(form.get("display_name")),
          email: String(form.get("email")),
          password: String(form.get("password"))
        });
        router.replace("/onboarding/legal");
      } else {
        await login({
          email: String(form.get("email")),
          password: String(form.get("password"))
        });
        const destination = new URLSearchParams(window.location.search).get("next");
        router.replace(
          destination?.startsWith("/") && !destination.startsWith("//")
            ? destination
            : "/briefing"
        );
      }
    } catch (error) {
      if (error instanceof ApiError && error.code === "MFA_REQUIRED") {
        router.push("/login/mfa");
      } else {
        setMessage(error instanceof Error ? error.message : "We could not complete that request.");
      }
    } finally {
      setSaving(false);
    }
  }

  async function sso(provider: "google" | "linkedin") {
    setSaving(true);
    setMessage("");
    try {
      const result = await beginSso(provider, signup ? "signup" : "login");
      window.location.assign(result.authorization_url);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : `${provider} sign-in is unavailable.`);
      setSaving(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-form-side">
        <Link className="wordmark" href="/" aria-label="Stem Cogent home">
          <StemMark />
          <span>Stem Cogent</span>
        </Link>
        <div className="auth-form-wrap">
          <p className="eyebrow">{signup ? "Start your workspace" : "Welcome back"}</p>
          <h1>{signup ? "Build decisions on verified intelligence." : "Sign in to Stem Cogent."}</h1>
          <p className="auth-lead">
            {signup
              ? "Create your company workspace and begin a 21-day trial. No invitation or card is required."
              : "Access your Decision Briefing, Company Lens, alerts, and evidence."}
          </p>
          <div className="sso-buttons">
            <button disabled={saving} onClick={() => void sso("google")} type="button"><b>G</b> Continue with Google</button>
            <button disabled={saving} onClick={() => void sso("linkedin")} type="button"><b>in</b> Continue with LinkedIn</button>
          </div>
          <div className="auth-divider"><span>or use work email</span></div>
          <form className="auth-form" onSubmit={submit}>
            {signup && (
              <div className="auth-field-row">
                <label><span>Your name</span><input autoComplete="name" name="display_name" required /></label>
                <label><span>Company</span><input autoComplete="organization" name="company_name" required /></label>
              </div>
            )}
            <label><span>Work email</span><input autoComplete="email" name="email" type="email" required /></label>
            <label>
              <span>Password</span>
              <span className="password-field">
                <input autoComplete={signup ? "new-password" : "current-password"} minLength={12} name="password" type={showPassword ? "text" : "password"} required />
                <button onClick={() => setShowPassword((value) => !value)} type="button">{showPassword ? "Hide" : "Show"}</button>
              </span>
            </label>
            {signup && (
              <label className="terms-check">
                <input name="terms" type="checkbox" required />
                <span>I agree to the <Link href="/legal/terms" target="_blank">Terms</Link> and acknowledge the <Link href="/legal/privacy" target="_blank">Privacy Notice</Link>.</span>
              </label>
            )}
            {message && <p className="form-message" role="alert">{message}</p>}
            <button className="primary-button auth-submit" disabled={saving} type="submit">{saving ? "Please wait…" : signup ? "Create workspace" : "Sign in"}</button>
          </form>
          <p className="auth-switch">
            {signup ? "Already have an account?" : "New to Stem Cogent?"}{" "}
            <Link href={signup ? "/login" : "/signup"}>{signup ? "Sign in" : "Create an account"}</Link>
          </p>
        </div>
        <p className="auth-footnote">© 2026 Stem Cogent · Decision intelligence with evidence in view.</p>
      </section>
      <aside className="auth-brand-side" aria-label="Stem Cogent product preview">
        <div className="auth-brand-copy">
          <p className="eyebrow">Structured. Fluid. Cogent.</p>
          <h2>Know what changed. Understand why it matters. Decide what comes next.</h2>
          <p>Built for Nigerian fintech leaders navigating regulation, infrastructure, competition, and growth.</p>
        </div>
        <div className="auth-preview" aria-hidden="true">
          <div className="preview-top"><span>My Decision Briefing</span><i>Illustrative product preview</i></div>
          <article><b>HIGH · REGULATORY</b><h3>New payment requirements need product review</h3><p>Why this matters to you · Matches your compliance priority and payment products.</p></article>
          <article><b>WATCHING · INFRASTRUCTURE</b><h3>Settlement reliability activity detected</h3><p>Evidence from configured dependencies is being monitored.</p></article>
        </div>
      </aside>
    </main>
  );
}
