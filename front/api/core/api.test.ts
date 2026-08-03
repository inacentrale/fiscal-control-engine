import { describe, expect, it, vi } from "vitest";

import { buildUrl, getApiBase, joinUrl } from "./api";

vi.mock("@/config", () => ({
  APP_CONFIG: {
    env: {
      API_URL: "http://localhost:8000",
      NEXT_PUBLIC_API_BASE_URL: "/api",
    },
  },
}));

describe("api core", () => {
  it("builds urls without params", () => {
    expect(buildUrl("health")).toBe("health");
  });

  it("appends query params and removes undefined values", () => {
    expect(buildUrl("excel/sheets", { fileId: "abc", page: undefined })).toBe(
      "excel/sheets?fileId=abc"
    );
  });

  it("joins base and paths without duplicate slashes", () => {
    expect(joinUrl("/api", "health")).toBe("/api/health");
    expect(joinUrl("/api/", "/health")).toBe("/api/health");
  });

  it("selects the server or browser API base", () => {
    expect(getApiBase(true)).toBe("http://localhost:8000");
    expect(getApiBase(false)).toBe("/api");
  });
});
