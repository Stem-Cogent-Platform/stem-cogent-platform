import { apiRequest } from "./api";
import type { MarketReportRecord } from "./types";

export const getMarketReports = () =>
  apiRequest<{ items: MarketReportRecord[] }>("/api/v1/market-reports");

export const getMarketReport = (sectorSlug: string, generateIfMissing = true) =>
  apiRequest<MarketReportRecord>(
    `/api/v1/market-reports/${encodeURIComponent(sectorSlug)}?generate_if_missing=${generateIfMissing}`
  );

export const generateMarketReport = (sectorSlug: string) =>
  apiRequest<MarketReportRecord>(
    `/api/v1/market-reports/${encodeURIComponent(sectorSlug)}/generate`,
    { method: "POST" }
  );
