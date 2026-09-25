"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function BriefingPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/radar");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 text-xs font-mono">
      Transitioning to Executive Radar...
    </div>
  );
}
