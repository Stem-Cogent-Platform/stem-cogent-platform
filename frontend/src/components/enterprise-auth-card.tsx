"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import { requestOtp, verifyOtp } from "@/lib/api";

type AuthMode = "login" | "signup";

export function EnterpriseAuthCard({ initialMode = "login" }: { initialMode?: AuthMode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get("return_to") ?? searchParams.get("next") ?? "";

  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [otpCode, setOtpCode] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (resendCooldown > 0) {
      timer = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [resendCooldown]);

  async function handleEmailSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid work or corporate email address.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const res = await requestOtp(email.trim());
      setSuccessMessage(res.message || "A 6-digit verification code has been dispatched.");
      setOtpCode(["", "", "", "", "", ""]);
      setStep("otp");
      setResendCooldown(30);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send verification code. Please retry.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(codeToVerify: string) {
    if (codeToVerify.length !== 6) {
      setError("Please enter all 6 digits of your verification code.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const authRes = await verifyOtp(email.trim(), codeToVerify);
      const user = authRes.user;

      // Smart routing based on tenant and user onboarding completion state
      if (!user.stage_a_completed) {
        router.push("/onboarding/stage-a");
      } else if (!user.stage_b_completed) {
        router.push("/onboarding/stage-b");
      } else if (returnUrl.startsWith("/") && !returnUrl.startsWith("//") && !returnUrl.includes("\\")) {
        router.push(returnUrl);
      } else {
        router.push("/radar");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid or expired verification code.");
      setLoading(false);
    }
  }

  function handleOtpDigitChange(index: number, val: string) {
    const cleaned = val.replace(/\D/g, "");
    if (!cleaned) {
      const next = [...otpCode];
      next[index] = "";
      setOtpCode(next);
      return;
    }

    // Support pasting multi-digit codes
    if (cleaned.length > 1) {
      const next = [...otpCode];
      for (let i = 0; i < 6 && index + i < 6 && i < cleaned.length; i++) {
        next[index + i] = cleaned[i];
      }
      setOtpCode(next);
      const targetIdx = Math.min(5, index + cleaned.length);
      otpInputRefs.current[targetIdx]?.focus();

      const combined = next.join("");
      if (combined.length === 6) {
        void handleVerify(combined);
      }
      return;
    }

    const next = [...otpCode];
    next[index] = cleaned[0];
    setOtpCode(next);

    if (index < 5 && cleaned[0]) {
      otpInputRefs.current[index + 1]?.focus();
    }

    const combined = next.join("");
    if (combined.length === 6) {
      void handleVerify(combined);
    }
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !otpCode[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
  }

  async function handleResendCode() {
    if (resendCooldown > 0 || loading) return;
    setError(null);
    setLoading(true);
    try {
      await requestOtp(email.trim());
      setSuccessMessage("A fresh 6-digit code has been dispatched to your email.");
      setOtpCode(["", "", "", "", "", ""]);
      setResendCooldown(30);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to resend code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4 sm:p-6 lg:p-8 font-sans">
      {/* Enterprise Split Canvas Layout */}
      <div className="w-full max-w-5xl bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* Left Authority Column: 40% Width on Large Screens */}
        <aside className="lg:col-span-5 bg-slate-950 text-white p-8 sm:p-10 flex flex-col justify-between relative overflow-hidden">
          {/* Subtle Ambient Radial Highlight */}
          <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-blue-500/20 border border-blue-500/30 text-blue-400">
                <StemMark compact />
              </div>
              <div>
                <span className="text-lg font-black tracking-tight text-white block">
                  Stem Cogent
                </span>
                <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400 block">
                  Systems Ltd
                </span>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <span className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-blue-900/60 border border-blue-700/60 text-[11px] font-mono font-semibold text-blue-300">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                Live Telemetry Mesh
              </span>
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight leading-snug">
                The Sovereign Pan-African Fintech Intelligence Engine
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Empowering C-Suite Executives, Chief Compliance Officers, and Treasury Leaders with continuous horizon monitoring and decision briefs.
              </p>
            </div>

            {/* Platform Metrics Chips */}
            <div className="pt-2 space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-300">CBN, SEC & NDPC Circulars</span>
                <span className="font-mono text-xs font-bold text-emerald-400">4,131+ Indexed</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-300">Switch & Rail Uptime Telemetry</span>
                <span className="font-mono text-xs font-bold text-blue-400">99.98% Monitored</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-300">Enterprise Trial Entitlement</span>
                <span className="font-mono text-xs font-bold text-purple-400">14-Day Pilot</span>
              </div>
            </div>
          </div>

          <div className="relative z-10 pt-8 mt-6 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
            <span>SOC2 Type II & NDPC Compliant</span>
            <span className="font-mono text-slate-500">v0.1.0-prod</span>
          </div>
        </aside>

        {/* Right Active Auth Canvas: 60% Width on Large Screens */}
        <section className="lg:col-span-7 p-8 sm:p-12 flex flex-col justify-center bg-white">
          <div className="max-w-md mx-auto w-full space-y-6">
            {step === "email" ? (
              <div className="space-y-6">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider mb-2">
                    Passwordless Verification
                  </div>
                  <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                    {mode === "login"
                      ? "Sign in to your enterprise workspace"
                      : "Create an enterprise workspace"}
                  </h1>
                  <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                    Enter your corporate work email to receive a secure 6-digit one-time passcode. No password maintenance required.
                  </p>
                </div>

                {error && (
                  <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium">
                    {error}
                  </div>
                )}

                <form onSubmit={handleEmailSubmit} className="space-y-4">
                  <div>
                    <label
                      htmlFor="email"
                      className="block text-xs font-bold uppercase tracking-wider text-slate-800 mb-1.5"
                    >
                      Corporate Work Email
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      placeholder="executive@fintech.ng"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10 shadow-2xs font-medium transition"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 px-4 rounded-xl shadow-sm text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 transition cursor-pointer active:scale-98"
                  >
                    {loading ? "Dispatching Code…" : "Send Verification Code →"}
                  </button>
                </form>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <span>
                    {mode === "login" ? "New to Stem Cogent?" : "Already have a workspace?"}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setMode((m) => (m === "login" ? "signup" : "login"));
                      setError(null);
                    }}
                    className="font-bold text-slate-900 hover:text-blue-600 underline underline-offset-2 transition-colors cursor-pointer"
                  >
                    {mode === "login" ? "Start 14-day free pilot" : "Sign in to workspace"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold tracking-wider uppercase text-emerald-600 font-mono">
                      Passcode Dispatched
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setStep("email");
                        setError(null);
                        setSuccessMessage(null);
                      }}
                      className="text-xs text-slate-500 hover:text-slate-900 underline font-medium"
                    >
                      Change email
                    </button>
                  </div>
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                    Enter Verification Code
                  </h2>
                  <p className="mt-1 text-xs text-slate-600">
                    A 6-digit OTP code has been dispatched to{" "}
                    <strong className="text-slate-900 font-semibold">{email}</strong>
                  </p>
                </div>

                {error && (
                  <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium">
                    {error}
                  </div>
                )}

                {successMessage && (
                  <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 font-medium">
                    {successMessage}
                  </div>
                )}

                <div className="space-y-5">
                  <div className="flex justify-between gap-2">
                    {otpCode.map((digit, idx) => (
                      <input
                        key={idx}
                        ref={(el) => {
                          otpInputRefs.current[idx] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={6}
                        value={digit}
                        onChange={(e) => handleOtpDigitChange(idx, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(idx, e)}
                        className="w-11 sm:w-12 h-14 text-center text-xl font-bold font-mono border border-slate-300 rounded-xl text-slate-900 bg-slate-50 focus:bg-white focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10 shadow-xs transition-all"
                      />
                    ))}
                  </div>

                  <button
                    type="button"
                    disabled={loading || otpCode.join("").length !== 6}
                    onClick={() => void handleVerify(otpCode.join(""))}
                    className="w-full py-3 px-4 rounded-xl shadow-sm text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 transition cursor-pointer active:scale-98"
                  >
                    {loading ? "Verifying Code…" : "Verify & Access Workspace →"}
                  </button>

                  <div className="text-center pt-2">
                    <button
                      type="button"
                      disabled={resendCooldown > 0 || loading}
                      onClick={handleResendCode}
                      className="text-xs text-slate-600 hover:text-slate-900 disabled:text-slate-400 font-semibold cursor-pointer"
                    >
                      {resendCooldown > 0
                        ? `Resend code in ${resendCooldown}s`
                        : "Didn't receive code? Resend passcode"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
