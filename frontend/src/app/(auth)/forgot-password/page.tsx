"use client";

import React, { FormEvent, useState } from "react";
import Link from "next/link";
import { StemMark } from "@/components/stem-mark";
import { forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid work email address.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await forgotPassword({ email: email.trim() });
      setSuccessMessage(
        res.message ||
          "If an account exists for this email, password reset instructions have been dispatched."
      );
      if (res.reset_token) {
        setResetToken(res.reset_token);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to dispatch reset instructions. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full space-y-4 sm:space-y-5">
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
          Forgot Password
        </h1>
        <p className="text-xs sm:text-sm text-[#64748B] font-normal">
          Enter your corporate work email to receive password reset instructions
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
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-800 space-y-2">
          <p>{successMessage}</p>
          {resetToken && (
            <div className="pt-2 border-t border-emerald-200/60">
              <span className="font-semibold block text-[11px] uppercase tracking-wider text-emerald-900 mb-1">
                Development / Direct Reset Link:
              </span>
              <Link
                href={`/reset-password?token=${encodeURIComponent(resetToken)}`}
                className="font-bold underline text-[#2A4BFF] hover:text-[#1E3AE5]"
              >
                Proceed to Reset Password ➔
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Form */}
      {!successMessage ? (
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div>
            <label
              htmlFor="email"
              className="block text-xs font-bold uppercase tracking-wider text-[#0B0F1A] mb-1.5"
            >
              Corporate Work Email
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
              "Sending Reset Instructions…"
            ) : (
              <>
                Send Reset Link <span>➔</span>
              </>
            )}
          </button>
        </form>
      ) : (
        <div className="pt-2">
          <Link
            href="/login"
            className="w-full py-3.5 px-4 rounded-xl text-sm font-bold text-white bg-[#2A4BFF] hover:bg-[#1E3AE5] active:bg-[#162ED0] transition cursor-pointer shadow-sm flex items-center justify-center"
          >
            Return to Sign In
          </Link>
        </div>
      )}

      {/* Footer Return Link */}
      <div className="pt-4 text-center text-xs sm:text-sm text-[#64748B]">
        Remember your password?{" "}
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
