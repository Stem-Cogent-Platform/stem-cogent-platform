"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import { StemMark } from "@/components/stem-mark";
import { acceptInvitation, validateInvitation } from "@/lib/api";
import { friendlyError } from "@/lib/product-copy/stateMessages";

type Invitation = { valid: true; workspace_name: string; email: string; expires_at: string };

function InvitationForm() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(token.length >= 32 ? "loading" : "error");
  const [message, setMessage] = useState(token.length >= 32 ? "" : "This invitation link is incomplete.");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    if (token.length < 32) return;
    void validateInvitation(token).then((data) => {
      if (!active) return;
      setInvitation(data);
      setStatus("ready");
    }).catch(() => {
      if (!active) return;
      setStatus("error");
      setMessage("This invitation is invalid, expired, or has already been used.");
    });
    return () => { active = false; };
  }, [token]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    try {
      await acceptInvitation({ token, display_name: displayName, password });
      router.replace("/onboarding/legal");
    } catch (error) {
      setMessage(friendlyError(error, "We couldn't accept this invitation. Ask your Stem contact for a new link."));
      setSubmitting(false);
    }
  }

  return (
    <main className="centered-state invite-page">
      <section className="state-card invite-card">
        <Link className="wordmark" href="/login"><StemMark compact /><span>Stem Cogent</span></Link>
        {status === "loading" && <div aria-busy="true" className="invite-loading"><span /><span /><span /></div>}
        {status === "error" && <><p className="eyebrow">Pilot invitation</p><h1>Invitation unavailable</h1><p>{message}</p><Link className="secondary-button" href="/login">Back to sign in</Link></>}
        {status === "ready" && invitation && <>
          <p className="eyebrow">You&apos;ve been invited to Stem Cogent</p>
          <h1>Join {invitation.workspace_name}</h1>
          <p>Your invitation is for <strong>{invitation.email}</strong>. Create your secure account to begin the guided setup.</p>
          <form className="invite-form" onSubmit={submit}>
            <label><span>Your name</span><input autoComplete="name" minLength={2} onChange={(event) => setDisplayName(event.target.value)} required value={displayName} /></label>
            <label><span>Create password</span><input autoComplete="new-password" minLength={12} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /><small>Use at least 12 characters.</small></label>
            {message && <p className="form-message" role="alert">{message}</p>}
            <button className="primary-button" disabled={submitting} type="submit">{submitting ? "Creating your account..." : "Accept invitation"}</button>
          </form>
          <p className="invite-expiry">This single-use link expires {new Date(invitation.expires_at).toLocaleString()}.</p>
        </>}
      </section>
    </main>
  );
}

export default function AcceptInvitationPage() {
  return <Suspense fallback={<main className="centered-state">Checking your invitation...</main>}><InvitationForm /></Suspense>;
}
