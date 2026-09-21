import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/search",
  useSearchParams: () => new URLSearchParams({ q: "What is the new CBN capital rule?" }),
}));

vi.mock("@/components/workspace-shell", () => ({
  WorkspaceShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-shell">{children}</div>
  ),
  navigation: [],
}));

vi.mock("@/lib/api", () => ({
  apiRequest: vi.fn((url: string) => {
    if (url.includes("/api/v1/search")) {
      return Promise.resolve({
        query: "What is the new CBN capital rule?",
        is_question: true,
        total_count: 0,
        briefs: [],
        intelligence: [],
        entities: [],
        cogent_inquiry: {
          prompt: "What is the new CBN capital rule?",
          suggested_angles: [
            "What does this mean for our business model and operations?",
            "How does this affect our competitors and market position?",
            "What regulatory or compliance requirements apply?",
          ],
        },
      });
    }
    return Promise.resolve({});
  }),
  recordProductEvent: vi.fn(),
}));

import SearchPage from "./page";

describe("Track 12 - Global Search & Ask Cogent Contract", () => {
  it("renders the Search & Ask Cogent surface with Chrome-style omnibox", () => {
    const markup = renderToStaticMarkup(<SearchPage />);

    expect(markup).toContain("Search &amp; Ask Cogent");
    expect(markup).toContain("Decision Intelligence Search");
  });
});
