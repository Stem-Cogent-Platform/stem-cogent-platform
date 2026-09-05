import { describe, expect, it } from "vitest";

import { friendlyError, stateMessages } from "./stateMessages";

describe("product state messages", () => {
  it("provides specific empty states for core pilot views", () => {
    expect(stateMessages.briefingEmpty.title).toContain("No decisions");
    expect(stateMessages.alertsEmpty.title).toContain("No alerts");
    expect(stateMessages.digestEmpty.body).toContain("digest");
    expect(stateMessages.companyBriefsEmpty.body).toContain("Company Context");
    expect(stateMessages.watchlistEmpty).toContain("Company Context");
    expect(stateMessages.focusEmpty).toContain("Focus Area");
  });

  it.each([
    [new Error("Network unavailable"), "Stem couldn't connect. Check your connection and try again."],
    [new Error("Service could not reach the API"), "Stem couldn't connect. Check your connection and try again."],
    [new Error("Request timeout"), "This is taking longer than expected. Try again."],
    [new Error("This took too long"), "This is taking longer than expected. Try again."],
    [new Error("Ordinary failure"), "Custom fallback"],
    ["not an Error", "Custom fallback"]
  ])("turns failures into safe product copy", (error, expected) => {
    expect(friendlyError(error, "Custom fallback")).toBe(expected);
  });

  it("uses the generic fallback when none is supplied", () => {
    expect(friendlyError(null)).toBe(stateMessages.genericError);
  });
});
