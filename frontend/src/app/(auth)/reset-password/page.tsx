"use client";

import React, { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import { resetPassword } from "@/lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function validateComplexity(val: string): string | null {
    if (val.length < 8) return "Password must be at least 8 characters long.";
    if (!/[A-Z]/.test(val)) return "Password must contain at least 1 uppercase letter.";
    if (!/[0-9]/.test(val)) return "Password must contain at least 1 number.";
    return null;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) {
      setError("Missing or invalid reset token. Please request a new password reset link.");
      return;
    }

    const complexityError = validateComplexity(password);
    if (complexityError) {
      setError(complexityError);
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please ensure both fields are identical.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await resetPassword({ token, password });
      setSuccess(true);
      setTimeout(() => {
        router.push("/login");
      }, 2500);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to reset password. The link may have expired."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full space-y-8">
      {/* Brand Mark */}
      <div>
        <Link href="/" className="inline-flex items-center gap-2.5 group">
          <StemMark compact />
          <span className="text-lg font-black tracking-tight text-[#0B0F1A]">
            Stem Cogent
          </span>
        </Link>
      </div>

      {/* Header Copy */}
      <div className="space-y-2">
        <h1 className="text-3xl sm:text-4xl font-black text-[#0B0F1A] tracking-tight">
          Set New Password
        </h1>
        <p className="text-sm sm:text-base text-[#64748B] font-normal">
          Create a secure password for your enterprise workspace
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div
          role="alert"
          className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-xs font-semibold text-[#DC2626]"
        >
          {error}
        </div>
      )}

      {/* Success Notification */}
      {success ? (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-800">
            Password updated successfully! Redirecting you to sign in…
          </div>
          <Link
            href="/login"
            className="w-full py-3.5 px-4 rounded-xl text-sm font-bold text-white bg-[#2A4BFF] hover:bg-[#1E3AE5] active:bg-[#162ED0] transition cursor-pointer shadow-sm flex items-center justify-center"
          >
            Sign In Now ➔
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* New Password */}
          <div>
            <label
              htmlFor="password"
              className="block text-xs font-bold uppercase tracking-wider text-[#0B0F1A] mb-1.5"
            >
              New Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                required
                autoComplete="new-password"
                placeholder="Min. 8 chars with 1 uppercase & 1 number"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                className="block w-full rounded-xl border border-[#E2E8F0] px-4 py-3 pr-12 text-sm text-[#0B0F1A] placeholder-[#64748B]/60 focus:border-[#2A4BFF] focus:outline-none focus:ring-2 focus:ring-[#2A4BFF]/15 transition font-medium bg-white"
              />
              <button
                type="button"
                id="toggle-password"
                aria-label={showPassword ? "Hide password" : "Show password"}
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-semibold text-[#64748B] hover:text-[#0B0F1A] transition cursor-pointer p-1"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Confirm Password */}
          <div>
            <label
              htmlFor="confirm_password"
              className="block text-xs font-bold uppercase tracking-wider text-[#0B0F1A] mb-1.5"
            >
              Confirm New Password
            </label>
            <input
              id="confirm_password"
              name="confirm_password"
              type={showPassword ? "text" : "password"}
              required
              autoComplete="new-password"
              placeholder="Re-enter your new password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (error) setError(null);
              }}
              className="block w-full rounded-xl border border-[#E2E8F0] px-4 py-3 text-sm text-[#0B0F1A] placeholder-[#64748B]/60 focus:border-[#2A4BFF] focus:outline-none focus:ring-2 focus:ring-[#2A4BFF]/15 transition font-medium bg-white"
            />
          </div>

          <button
            id="submit_button"
            type="submit"
            disabled={loading}
            className="w-full py-3.5 px-4 rounded-xl text-sm font-bold text-white bg-[#2A4BFF] hover:bg-[#1E3AE5] active:bg-[#162ED0] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2A4BFF] disabled:opacity-50 transition cursor-pointer shadow-sm flex items-center justify-center gap-2"
          >
            {loading ? (
              "Updating Password…"
            ) : (
              <>
                Update Password <span>➔</span>
              </>
            )}
          </button>
        </form>
      )}

      {/* Footer Return Link */}
      <div className="pt-4 text-center text-xs sm:text-sm text-[#64748B]">
        Back to{" "}
        <Link
          href="/login"
          className="font-bold text-[#2A4BFF] hover:text-[#1E3AE5] hover:underline transition-colors"
        >
          Sign In
        </Link>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="text-sm text-slate-400">Loading password reset…</div>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
