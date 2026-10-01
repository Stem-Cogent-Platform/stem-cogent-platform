import React from "react";
import { AuthHeroShowcase } from "@/components/auth-hero-showcase";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#F8FAFC]">
      {/* LEFT: AUTH FORM CANVAS (50% or max-w-xl centered) */}
      <main className="w-full lg:w-1/2 min-h-screen lg:h-screen lg:overflow-y-auto flex flex-col justify-between px-6 py-6 sm:px-10 sm:py-8 lg:px-12 xl:px-16 bg-[#FFFFFF]">
        <div className="w-full max-w-lg mx-auto my-auto py-2">
          {children}
        </div>
        <footer className="mt-6 pt-3 border-t border-slate-100 text-center text-xs text-[#64748B] shrink-0">
          © {new Date().getFullYear()} Stem Cogent Systems Ltd. All rights reserved.
        </footer>
      </main>

      {/* RIGHT: PRODUCT HERO SHOWCASE (50% Cobalt Canvas: #2A4BFF) */}
      <aside className="hidden lg:flex lg:w-1/2 lg:h-screen lg:sticky lg:top-0 p-4 xl:p-6 bg-[#F8FAFC] overflow-hidden">
        <div className="w-full h-full bg-[#2A4BFF] rounded-3xl relative overflow-hidden flex flex-col justify-between p-8 xl:p-12 text-white shadow-2xl">
          <AuthHeroShowcase />
        </div>
      </aside>
    </div>
  );
}
