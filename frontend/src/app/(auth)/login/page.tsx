"use client";

import React, { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import { login } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get("return_to") ?? searchParams.get("next") ?? "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid work email address.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await login({ email: email.trim(), password });
      const user = res.user;

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
      setError(err instanceof Error ? err.message : "Invalid email or password. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="w-full space-y-4 sm:space-y-4.5">
      {/* Brand Mark */}
      <div>
        <Link href="/" className="inline-flex items-center gap-2 group">
          <StemMark compact />
          <span className="text-lg font-black tracking-tight text-[#0B0F1A]">
            Stem Cogent
          </span>
        </Link>
      </div>

      {/* Header Copy */}
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-black text-[#0B0F1A] tracking-tight">
          Welcome Back
        </h1>
        <p className="text-xs sm:text-sm text-[#64748B] font-normal">
          Enter your credentials to access your enterprise workspace
        </p>
      </div>

      {/* Social Auth Providers (Reference Match) */}
      <div className="grid grid-cols-2 gap-2.5">
        <button
          type="button"
          onClick={() => {
            setError("Google single sign-on is managed via SAML/SSO for enterprise domains. Use corporate email below.");
          }}
          className="flex items-center justify-center gap-2 px-3 py-2 rounded-xl border border-[#E2E8F0] hover:bg-slate-50 hover:border-slate-300 transition text-xs font-semibold text-[#0B0F1A] shadow-xs cursor-pointer"
        >
          <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>Log in with Google</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setError("Apple authentication is restricted to verified tenant directories. Use corporate email below.");
          }}
          className="flex items-center justify-center gap-2 px-3 py-2 rounded-xl border border-[#E2E8F0] hover:bg-slate-50 hover:border-slate-300 transition text-xs font-semibold text-[#0B0F1A] shadow-xs cursor-pointer"
        >
          <svg className="w-4 h-4 shrink-0 fill-current text-black" viewBox="0 0 24 24">
            <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.89c.65-.8 1.1-1.92.97-3.04-1 .04-2.14.67-2.82 1.46-.59.68-1.12 1.8-1 2.89 1.11.08 2.22-.56 2.85-1.31" />
          </svg>
          <span>Log in with Apple</span>
        </button>
      </div>

      {/* Horizontal Divider */}
      <div className="relative flex items-center justify-center">
        <div className="w-full border-t border-slate-200" />
        <span className="absolute bg-white px-2.5 text-[11px] text-[#64748B] font-medium uppercase tracking-wider">
          or
        </span>
      </div>

      {/* Error Alert */}
      {error && (
        <div
          role="alert"
          className="p-3 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-xs font-semibold text-[#DC2626]"
        >
          {error}
        </div>
      )}

      {/* Login Form */}
      <form onSubmit={handleSubmit} className="space-y-3" noValidate>
        {/* Work Email Address */}
        <div>
          <label
            htmlFor="email"
            className="block text-[11px] font-bold uppercase tracking-wider text-[#0B0F1A] mb-1"
          >
            Email address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="executive@fintech.ng"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (error) setError(null);
            }}
            className="block w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm text-[#0B0F1A] placeholder-[#64748B]/60 focus:border-[#2A4BFF] focus:outline-none focus:ring-2 focus:ring-[#2A4BFF]/15 transition font-medium bg-white"
          />
        </div>

        {/* Password */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label
              htmlFor="password"
              className="block text-[11px] font-bold uppercase tracking-wider text-[#0B0F1A]"
            >
              Password
            </label>
            <Link
              href="/forgot-password"
              className="text-[11px] font-semibold text-[#2A4BFF] hover:underline hover:text-[#1E3AE5]"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              required
              autoComplete="current-password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (error) setError(null);
              }}
              className="block w-full rounded-xl border border-[#E2E8F0] px-3 py-2 pr-14 text-sm text-[#0B0F1A] placeholder-[#64748B]/60 focus:border-[#2A4BFF] focus:outline-none focus:ring-2 focus:ring-[#2A4BFF]/15 transition font-medium bg-white"
            />
            <button
              type="button"
              id="toggle-password"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-semibold text-[#64748B] hover:text-[#0B0F1A] hover:bg-slate-100 transition cursor-pointer"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {showPassword ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                )}
              </svg>
              <span>{showPassword ? "Hide" : "Show"}</span>
            </button>
          </div>
        </div>

        {/* Remember me toggle */}
        <div className="pt-0.5">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded border-[#E2E8F0] text-[#2A4BFF] focus:ring-[#2A4BFF] transition cursor-pointer"
            />
            <span className="text-xs text-[#64748B]">Keep me signed in on this device</span>
          </label>
        </div>

        {/* Primary Submit Button */}
        <button
          id="submit_button"
          type="submit"
          disabled={loading}
          className="w-full py-3 px-4 rounded-xl text-sm font-bold text-white bg-[#2A4BFF] hover:bg-[#1E3AE5] active:bg-[#162ED0] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2A4BFF] disabled:opacity-50 transition cursor-pointer shadow-md hover:shadow-lg flex items-center justify-center gap-2 mt-1.5"
        >
          {loading ? (
            "Authenticating…"
          ) : (
            <>
              Sign In <span>➔</span>
            </>
          )}
        </button>
      </form>

      {/* Footer Switch Link */}
      <div className="pt-1 text-center text-xs text-[#64748B]">
        Don&apos;t have an account?{" "}
        <Link
          href="/signup"
          className="font-bold text-[#2A4BFF] hover:text-[#1E3AE5] hover:underline transition-colors"
        >
          Start 14-day free trial
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="text-sm text-slate-400">Loading sign in…</div>}>
      <LoginForm />
    </Suspense>
  );
}
