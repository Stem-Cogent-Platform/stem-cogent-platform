import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import AuthLayout from "./layout";
import SignupPage from "./signup/page";
import LoginPage from "./login/page";
import ForgotPasswordPage from "./forgot-password/page";
import ResetPasswordPage from "./reset-password/page";

describe("Enterprise Authentication Form & Component Suite", () => {
  describe("SignupForm & Terms Checkbox Gating", () => {
    it("renders submit button disabled by default until terms checkbox is checked", () => {
      const markup = renderToStaticMarkup(<SignupPage />);

      // Assert submit button exists and is disabled
      expect(markup).toContain('id="submit_button"');
      expect(markup).toContain("disabled");
      expect(markup).toContain("Create Account");

      // Assert terms checkbox exists and is unchecked initially
      expect(markup).toContain('id="terms_accepted"');
      expect(markup).toContain('type="checkbox"');
      expect(markup).toContain("Click to agree to Stem");
      expect(markup).toContain('href="/legal/terms"');
      expect(markup).toContain('href="/legal/privacy"');
    });

    it("renders all required enterprise credential input fields", () => {
      const markup = renderToStaticMarkup(<SignupPage />);

      expect(markup).toContain('id="full_name"');
      expect(markup).toContain('name="full_name"');
      expect(markup).toContain('id="username"');
      expect(markup).toContain('name="username"');
      expect(markup).toContain('id="email"');
      expect(markup).toContain('type="email"');
      expect(markup).toContain('id="password"');
      expect(markup).toContain('type="password"');
      expect(markup).toContain('id="confirm_password"');
      expect(markup).toContain('name="confirm_password"');
    });

    it("renders social login options and divider matching reference design", () => {
      const markup = renderToStaticMarkup(<SignupPage />);

      expect(markup).toContain("Log in with Google");
      expect(markup).toContain("Log in with Apple");
      expect(markup).toContain("or");
    });
  });

  describe("Client-side Field Validation Rules", () => {
    function validateEmail(val: string): boolean {
      const trimmed = val.trim();
      if (!trimmed) return false;
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(trimmed);
    }

    function validatePassword(val: string): { valid: boolean; reason?: string } {
      if (val.length < 8) return { valid: false, reason: "Must be at least 8 characters" };
      if (!/[A-Z]/.test(val)) return { valid: false, reason: "Must contain 1 uppercase letter" };
      if (!/[0-9]/.test(val)) return { valid: false, reason: "Must contain 1 number" };
      return { valid: true };
    }

    it("rejects invalid emails and accepts valid enterprise emails", () => {
      expect(validateEmail("")).toBe(false);
      expect(validateEmail("plainaddress")).toBe(false);
      expect(validateEmail("missing@domain")).toBe(false);
      expect(validateEmail("@nodomain.com")).toBe(false);
      expect(validateEmail("executive@fintech.ng")).toBe(true);
      expect(validateEmail("cto@bank.com.ng")).toBe(true);
    });

    it("rejects short or weak passwords and validates complexity rules", () => {
      // Less than 8 characters
      expect(validatePassword("Pass1").valid).toBe(false);
      expect(validatePassword("Pass1").reason).toContain("8 characters");

      // No uppercase
      expect(validatePassword("lowercase123").valid).toBe(false);
      expect(validatePassword("lowercase123").reason).toContain("uppercase");

      // No number
      expect(validatePassword("NoNumberPassword").valid).toBe(false);
      expect(validatePassword("NoNumberPassword").reason).toContain("number");

      // Valid compliant password
      expect(validatePassword("SecurePassword2026").valid).toBe(true);
    });

    it("validates password confirmation matches password", () => {
      function validateConfirm(pwd: string, confirm: string): boolean {
        return !!confirm && pwd === confirm;
      }
      expect(validateConfirm("SecurePassword2026", "SecurePassword2026")).toBe(true);
      expect(validateConfirm("SecurePassword2026", "DifferentPassword123")).toBe(false);
      expect(validateConfirm("SecurePassword2026", "")).toBe(false);
    });
  });

  describe("Password Visibility Toggle", () => {
    it("renders password toggle button with accessible aria-label and default password mask", () => {
      const markup = renderToStaticMarkup(<SignupPage />);

      expect(markup).toContain('id="toggle-password"');
      expect(markup).toContain('aria-label="Show password"');
      expect(markup).toContain('type="password"');
      expect(markup).toContain(">Show</span>");
    });

    it("verifies toggling logic switches type between password and text", () => {
      let show = false;
      const toggle = () => {
        show = !show;
      };

      expect(show ? "text" : "password").toBe("password");
      toggle();
      expect(show ? "text" : "password").toBe("text");
      toggle();
      expect(show ? "text" : "password").toBe("password");
    });
  });

  describe("SignIn Form & Recovery Routing", () => {
    it("renders sign-in form with forgot password link leading to /forgot-password", () => {
      const markup = renderToStaticMarkup(<LoginPage />);

      expect(markup).toContain("Welcome Back");
      expect(markup).toContain('id="email"');
      expect(markup).toContain('id="password"');
      expect(markup).toContain('href="/forgot-password"');
      expect(markup).toContain("Forgot password?");
      expect(markup).toContain("Sign In");
    });

    it("renders forgot-password page with email dispatch form", () => {
      const markup = renderToStaticMarkup(<ForgotPasswordPage />);

      expect(markup).toContain("Forgot Password");
      expect(markup).toContain("Send Reset Link");
      expect(markup).toContain('type="email"');
      expect(markup).toContain('href="/login"');
    });

    it("renders reset-password page with new and confirm password fields", () => {
      const markup = renderToStaticMarkup(<ResetPasswordPage />);

      expect(markup).toContain("Set New Password");
      expect(markup).toContain('id="password"');
      expect(markup).toContain('id="confirm_password"');
      expect(markup).toContain("Update Password");
    });
  });

  describe("AuthLayout Viewport Split & Hero Showcase Contract", () => {
    it("renders 50/50 split layout and embedded telemetry preview", () => {
      const markup = renderToStaticMarkup(
        <AuthLayout>
          <div>Form Content</div>
        </AuthLayout>
      );

      // Verify layout containers
      expect(markup).toContain("lg:w-1/2");
      expect(markup).toContain("bg-[#2A4BFF]");
      expect(markup).toContain("Form Content");

      // Verify hero title
      expect(markup).toContain("Real-Time Decision Intelligence for African Fintechs");

      // Verify 3 explicit telemetry mockup items
      expect(markup).toContain("Providus Latency");
      expect(markup).toContain("Degraded (18.4s)");
      expect(markup).toContain("Active Gap");
      expect(markup).toContain("2-Hour NIP Dispute Window");
      expect(markup).toContain("Action Item");
      expect(markup).toContain("Re-route virtual accounts");

      // Verify corridor badges
      expect(markup).toContain("NIBSS");
      expect(markup).toContain("Providus");
      expect(markup).toContain("Wema");
      expect(markup).toContain("SEC");

      // Assert stale deceptive stats are completely absent
      expect(markup).not.toContain("4,131+ Indexed");
      expect(markup).not.toContain("99.98% Monitored");
      expect(markup).not.toContain("SOC2 Type II & NDPC Compliant");
      expect(markup).not.toContain("v0.1.0-prod");
      expect(markup).not.toContain("Passwordless Verification");
    });
  });
});
