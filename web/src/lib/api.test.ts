import { describe, expect, it } from "vitest";

import { toApiError } from "./api";

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("toApiError", () => {
  it("reads the API's error envelope", async () => {
    const error = await toApiError(
      jsonResponse(401, {
        error: { code: "unauthenticated", message: "Sign in again.", request_id: "abc" },
      }),
    );
    expect(error.status).toBe(401);
    expect(error.code).toBe("unauthenticated");
    expect(error.message).toBe("Sign in again.");
    expect(error.requestId).toBe("abc");
    expect(error.isAuthError).toBe(true);
  });

  it("falls back to a plain message when the body is not JSON", async () => {
    const error = await toApiError(
      new Response("<html>Bad gateway</html>", { status: 502, headers: { "X-Request-ID": "r1" } }),
    );
    expect(error.code).toBe("request_failed");
    expect(error.message).toBe("The server had a problem. Try again in a minute.");
    expect(error.requestId).toBe("r1");
  });

  it("ignores fields of the wrong type", async () => {
    const error = await toApiError(jsonResponse(400, { error: { code: 7, message: ["x"] } }));
    expect(error.code).toBe("request_failed");
    expect(error.message).toBe("That request didn't work.");
  });
});
