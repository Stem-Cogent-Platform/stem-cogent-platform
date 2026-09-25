"use client";

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div className="h-5 w-40 rounded bg-slate-200" />
        <div className="h-6 w-20 rounded-full bg-slate-100" />
      </div>
      <div className="space-y-2">
        <div className="h-4 w-full rounded bg-slate-100" />
        <div className="h-4 w-5/6 rounded bg-slate-100" />
      </div>
      <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-100">
        <div className="h-8 rounded bg-slate-100" />
        <div className="h-8 rounded bg-slate-100" />
        <div className="h-8 rounded bg-slate-100" />
      </div>
    </div>
  );
}

export function GapMatrixSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm animate-pulse space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div className="space-y-2">
          <div className="h-4 w-28 rounded bg-blue-100" />
          <div className="h-7 w-72 rounded bg-slate-200" />
        </div>
        <div className="h-10 w-44 rounded-xl bg-slate-100" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-5 space-y-4">
          <div className="h-4 w-32 rounded bg-slate-200" />
          <div className="h-16 rounded bg-slate-200/60" />
          <div className="h-12 rounded bg-slate-200/60" />
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-5 space-y-4">
          <div className="h-4 w-36 rounded bg-slate-200" />
          <div className="h-16 rounded bg-slate-200/60" />
          <div className="h-12 rounded bg-slate-200/60" />
        </div>
      </div>
      <div className="space-y-3 pt-2">
        <div className="h-4 w-48 rounded bg-slate-200" />
        <div className="h-12 rounded-lg bg-slate-100" />
        <div className="h-12 rounded-lg bg-slate-100" />
      </div>
    </div>
  );
}

export function TelemetrySkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="h-4 w-24 rounded bg-slate-200" />
            <div className="h-3 w-3 rounded-full bg-slate-200" />
          </div>
          <div className="h-8 w-28 rounded bg-slate-200" />
          <div className="h-3 w-36 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}
