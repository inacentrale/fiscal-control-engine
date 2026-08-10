import { describe, expect, it } from "vitest";

import {
  AGENT_STREAM_TIMEOUT_MS,
  isAgentStreamTimeoutError,
} from "./runAgentAnalysis";

describe("runAgentAnalysis", () => {
  it("borne l'attente du stream agent", () => {
    expect(AGENT_STREAM_TIMEOUT_MS).toBe(90_000);
    expect(
      isAgentStreamTimeoutError(new DOMException("timeout", "TimeoutError"))
    ).toBe(true);
    expect(isAgentStreamTimeoutError(new Error("network"))).toBe(false);
  });
});
