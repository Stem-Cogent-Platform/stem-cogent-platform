import { apiRequest } from "./api";
import type { MarketReportRecord } from "./types";

export interface MarketReportStatusResponse {
  status: "idle" | "processing" | "completed" | "failed";
  sector_slug: string;
  error?: string;
  report?: MarketReportRecord;
}

export const getMarketReports = () =>
  apiRequest<{ items: MarketReportRecord[] }>("/api/v1/market-reports");

export const getMarketReport = (sectorSlug: string, generateIfMissing = true, refresh = false) =>
  apiRequest<MarketReportRecord & { status?: string }>(
    `/api/v1/market-reports/${encodeURIComponent(sectorSlug)}?generate_if_missing=${generateIfMissing}&refresh=${refresh}`
  );

export const getMarketReportStatus = (sectorSlug: string) =>
  apiRequest<MarketReportStatusResponse>(
    `/api/v1/market-reports/${encodeURIComponent(sectorSlug)}/status`
  );

export const generateMarketReport = (sectorSlug: string) =>
  apiRequest<{ status: string; sector_slug: string }>(
    `/api/v1/market-reports/${encodeURIComponent(sectorSlug)}/generate`,
    { method: "POST" }
  );
