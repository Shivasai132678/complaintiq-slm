import { expect, it, vi } from "vitest";
import { api } from "./api";
it("submits complaint through the configured engine", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ id: "CQ-1" }) });
  vi.stubGlobal("fetch", fetcher);
  await api.analyze("A disputed fee");
  expect(fetcher).toHaveBeenCalledWith(
    "/api/complaints",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ text: "A disputed fee" }),
    }),
  );
});
it("surfaces the backend validation reason", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Narrative is required" }),
    }),
  );
  await expect(api.analyze("")).rejects.toThrow("Narrative is required");
});
it("surfaces structured service errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        error: {
          code: "MODEL_ERROR",
          message: "The baseline could not load",
        },
      }),
    }),
  );
  await expect(api.analyze("fee complaint")).rejects.toThrow(
    "The baseline could not load",
  );
});
