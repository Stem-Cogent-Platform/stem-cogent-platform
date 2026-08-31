"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { adminMfaLogin } from "@/lib/api";

function AdminLoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setMessage("");
    try { await adminMfaLogin({ email, password, totp_code: code }); router.replace(params.get("next")?.startsWith("/internal/admin") ? params.get("next")! : "/internal/admin/tenants"); }
    catch { setMessage("Authentication failed. Check your credentials and current authenticator code."); setSubmitting(false); }
  }
  return <main className="centered-state internal-login"><form className="state-card invite-form" onSubmit={submit}><p className="eyebrow">Stem operations</p><h1>Operator sign in</h1><p>Password and a current authenticator code are required. Tenant administrators cannot use this console.</p><label><span>Email</span><input autoComplete="username" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></label><label><span>Password</span><input autoComplete="current-password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /></label><label><span>Authenticator code</span><input autoComplete="one-time-code" inputMode="numeric" maxLength={6} minLength={6} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} pattern="[0-9]{6}" required value={code} /></label>{message && <p className="form-message" role="alert">{message}</p>}<button className="primary-button" disabled={submitting} type="submit">{submitting ? "Verifying..." : "Continue securely"}</button></form></main>;
}

export default function InternalLoginPage() { return <Suspense fallback={<main className="centered-state">Preparing secure sign-in...</main>}><AdminLoginForm /></Suspense>; }
