import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import App from "./App";
import { api } from "./api";
import type { Complaint, Analytics } from "./types";
vi.mock("./api", () => ({
  api: {
    complaints: vi.fn(),
    analytics: vi.fn(),
    analyze: vi.fn(),
    evaluation: vi.fn(),
    batch: vi.fn(),
  },
}));
const complaint: Complaint = {
  id: "CQ-TEST",
  text: "My bank charged an unexpected overdraft fee.",
  product: "Checking or savings account",
  issue: "Fees",
  priority: "Medium",
  priority_reason: "Rule matched overdraft fee.",
  department: "Deposit Operations Team",
  action: "Review the account fee.",
  summary: "My bank charged an unexpected overdraft fee.",
  status: "Queued",
  backend: "baseline",
  model_version: "baseline-test",
  latency_ms: 200,
  created_at: "2026-10-02T10:00:00Z",
  explanation: [{ token: "bank", weight: 0.15 }],
};
const analytics: Analytics = {
  total: 1,
  by_product: { "Checking or savings account": 1 },
  by_priority: { Medium: 1 },
  by_department: { "Deposit Operations Team": 1 },
  by_backend: { baseline: 1 },
  needs_review: 0,
  average_latency_ms: 200,
};
beforeEach(() => {
  vi.mocked(api.complaints).mockResolvedValue({ items: [complaint] });
  vi.mocked(api.analytics).mockResolvedValue(analytics);
  vi.mocked(api.analyze).mockResolvedValue(complaint);
  vi.mocked(api.batch).mockResolvedValue({ items: [complaint], saved: 1 });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
describe("complaint operations workflow", () => {
  it("shows actual saved case data and only analyzes when explicitly submitted", async () => {
    render(<App />);
    await screen.findByText("CQ-TEST");
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
    const input = screen.getByLabelText("Complaint narrative");
    fireEvent.change(input, {
      target: { value: "My checking account has an incorrect fee." },
    });
    expect(api.analyze).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Analyze complaint" }));
    await screen.findByText("Saved to queue");
    expect(api.analyze).toHaveBeenCalledTimes(1);
    expect(api.analyze).toHaveBeenCalledWith(
      "My checking account has an incorrect fee.",
    );
  });
  it("shows actionable analysis errors without displaying a fabricated result", async () => {
    vi.mocked(api.analyze).mockRejectedValue(new Error("Model unavailable"));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
    fireEvent.change(screen.getByLabelText("Complaint narrative"), {
      target: { value: "A bank fee complaint" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze complaint" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Model unavailable",
    );
    expect(screen.queryByText("Saved to queue")).not.toBeInTheDocument();
  });
  it("filters saved cases and opens an inspectable accessible drawer", async () => {
    render(<App />);
    await screen.findByText("CQ-TEST");
    fireEvent.click(screen.getByRole("button", { name: /^Cases/ }));
    fireEvent.change(screen.getByLabelText("Search complaints"), {
      target: { value: "unmatched" },
    });
    expect(screen.getByText("No matching cases")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search complaints"), {
      target: { value: "overdraft" },
    });
    fireEvent.click(screen.getByRole("button", { name: "CQ-TEST" }));
    const dialog = screen.getByRole("dialog", { name: "Case CQ-TEST" });
    expect(within(dialog).getByText("Original narrative")).toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: "Close case details" }),
    ).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("validates CSV schema and processes uploaded narratives only on click", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Batch upload" }));
    const input = screen.getByLabelText("Upload complaint CSV");
    fireEvent.change(input, {
      target: {
        files: [
          new File(["wrong\nexample"], "wrong.csv", { type: "text/csv" }),
        ],
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "column named text",
    );
    fireEvent.change(input, {
      target: {
        files: [
          new File(['text\n"My bank charged an incorrect fee."'], "valid.csv", {
            type: "text/csv",
          }),
        ],
      },
    });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Analyze 1 complaints/ }),
      ).toBeEnabled(),
    );
    expect(api.batch).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: /Analyze 1 complaints/ }),
    );
    await screen.findByText("1 complaints saved to your queue");
    expect(api.batch).toHaveBeenCalledWith([
      "My bank charged an incorrect fee.",
    ]);
    expect(
      screen.getByRole("button", { name: /Analyze 1 complaints/ }),
    ).toBeDisabled();
  });
});
it("prevents double submission while inference is in progress", async () => {
  let resolve: ((value: Complaint) => void) | undefined;
  vi.mocked(api.analyze).mockImplementation(
    () =>
      new Promise<Complaint>((finish) => {
        resolve = finish;
      }),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
  const input = screen.getByLabelText("Complaint narrative");
  fireEvent.change(input, {
    target: { value: "A bank overdraft fee complaint" },
  });
  const form = input.closest("form")!;
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(api.analyze).toHaveBeenCalledTimes(1);
  resolve?.(complaint);
  await screen.findByText("Saved to queue");
});
