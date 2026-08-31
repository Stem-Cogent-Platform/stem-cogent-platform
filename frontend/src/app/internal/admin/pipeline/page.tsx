"use client";

import { useCallback, useEffect, useState } from "react";
import { InternalAdminShell } from "@/components/internal-admin-shell";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Pipeline = { active_sources: number; failed_jobs: number; completed_outputs: number; active_activations: number };
export default function AdminPipelinePage() {
  const [state, setState] = useState<LoadState<Pipeline>>({ status: "loading" });
  const load = useCallback(async () => { try { setState({ status: "ready", data: await apiRequest<Pipeline>("/api/v1/internal/admin/pipeline") }); } catch { setState({ status: "error", message: "Pipeline status could not be loaded." }); } }, []);
  useEffect(() => { const timer = setTimeout(() => void load(), 0); return () => clearTimeout(timer); }, [load]);
  return <InternalAdminShell><header className="internal-heading"><div><p className="eyebrow">Operational readiness</p><h1>Pipeline</h1></div><button className="secondary-button" onClick={() => void load()} type="button">Refresh</button></header>{state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}{state.status === "ready" && <section className="admin-metric-grid"><article><span>Active sources</span><strong>{state.data.active_sources}</strong></article><article><span>Failed jobs</span><strong>{state.data.failed_jobs}</strong></article><article><span>Completed outputs</span><strong>{state.data.completed_outputs}</strong></article><article><span>Active activations</span><strong>{state.data.active_activations}</strong></article></section>}</InternalAdminShell>;
}
