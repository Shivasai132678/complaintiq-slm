import type { Analytics, BatchResult, Complaint, Evaluation } from "./types";
async function request<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(
    `/api/${path}`,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const detail: unknown = await response.json();
      if (detail && typeof detail === "object") {
        if ("detail" in detail && typeof detail.detail === "string")
          message = detail.detail;
        if (
          "error" in detail &&
          detail.error &&
          typeof detail.error === "object" &&
          "message" in detail.error &&
          typeof detail.error.message === "string"
        )
          message = detail.error.message;
      }
    } catch {
      /* Preserve readable HTTP error. */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export const api = {
  complaints: () => request<{ items: Complaint[] }>("complaints"),
  analytics: () => request<Analytics>("analytics"),
  evaluation: () => request<Evaluation>("evaluation"),
  analyze: (text: string) =>
    request<Complaint>("complaints", { text, backend: "baseline" }),
  batch: (texts: string[]) =>
    request<BatchResult>("batch", { texts, backend: "baseline" }),
};
