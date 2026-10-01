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
      <main className="w-full lg:w-1/2 min-h-screen flex flex-col justify-between px-6 py-8 sm:px-12 sm:py-10 lg:px-14 xl:px-16 lg:py-12 bg-[#FFFFFF]">
        <div className="w-full max-w-lg mx-auto flex-1 flex flex-col justify-center">
          {children}
        </div>
        <footer className="mt-8 pt-4 border-t border-slate-100 text-center text-xs text-[#64748B]">
          © {new Date().getFullYear()} Stem Cogent Systems Ltd. All rights reserved.
        </footer>
      </main>

      {/* RIGHT: PRODUCT HERO SHOWCASE (50% Cobalt Canvas: #2A4BFF) */}
      <aside className="hidden lg:flex lg:w-1/2 min-h-screen p-4 xl:p-6 bg-[#F8FAFC]">
        <div className="w-full h-full bg-[#2A4BFF] rounded-3xl relative overflow-hidden flex flex-col justify-between p-10 xl:p-14 text-white shadow-2xl">
          <AuthHeroShowcase />
        </div>
      </aside>
    </div>
  );
}
