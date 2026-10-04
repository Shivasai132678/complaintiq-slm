import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import App from "./App";
import { ApiError, pilot } from "./pilot-api";
import type { Case, Job } from "./pilot-api";
vi.mock("./pilot-api", async (original) => ({
  ...(await original<typeof import("./pilot-api")>()),
  pilot: {
    config: vi.fn(),
    health: vi.fn(),
    cases: vi.fn(),
    case: vi.fn(),
    review: vi.fn(),
    note: vi.fn(),
    transition: vi.fn(),
    jobs: vi.fn(),
    job: vi.fn(),
    submit: vi.fn(),
    overview: vi.fn(),
    system: vi.fn(),
    backup: vi.fn(),
    evaluation: vi.fn(),
    control: vi.fn(),
  },
}));
const original = {
  id: "CQ-ONE",
  text: "A duplicate charge on my credit card.",
  product: "Credit card",
  issue: "Billing disputes",
  priority: "Low",
  priority_reason: "No risk phrase",
  department: "Card Services Team",
  action: "Review",
  summary: "A duplicate charge.",
  status: "Queued",
  backend: "slm",
  model_version: "Qwen-test.gguf",
  latency_ms: 900,
  created_at: "2026-10-04T00:00:00Z",
  explanation: [],
};
const item: Case = {
  ...original,
  confirmed: 0,
  review_flag: 0,
  revision: 1,
  updated_at: original.created_at,
  original,
  events: [],
};
beforeEach(() => {
  vi.stubGlobal("scrollTo", vi.fn());
  history.replaceState({}, "", "/cases");
  vi.mocked(pilot.config).mockResolvedValue({
    taxonomy: { "Credit card": ["Billing disputes", "Fees or interest"] },
    departments: ["Card Services Team", "Manual Review Team"],
    routing: { "Credit card": "Card Services Team" },
    outside: "Outside supported scope",
  });
  vi.mocked(pilot.health).mockResolvedValue({
    backend: "slm",
    model_version: "Qwen-test.gguf",
    slm_status: "ready",
    training_status: "trained_exported",
    training_size: 9000,
  });
  vi.mocked(pilot.cases).mockResolvedValue({
    items: [item],
    total: 1,
    page: 1,
    page_size: 25,
  });
  vi.mocked(pilot.case).mockResolvedValue(item);
  vi.mocked(pilot.jobs).mockResolvedValue({ items: [] });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("keeps filters in the URL and requests the filtered server page", async () => {
  render(<App />);
  await screen.findByText("CQ-ONE");
  fireEvent.change(screen.getByLabelText("Search cases"), {
    target: { value: "duplicate" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply search" }));
  await waitFor(() =>
    expect(pilot.cases).toHaveBeenLastCalledWith("q=duplicate"),
  );
  expect(location.search).toBe("?q=duplicate");
  fireEvent.change(screen.getByLabelText("Priority filter"), {
    target: { value: "High" },
  });
  await waitFor(() =>
    expect(pilot.cases).toHaveBeenLastCalledWith("q=duplicate&priority=High"),
  );
  expect(screen.getByRole("link", { name: "Export filtered" })).toHaveAttribute(
    "href",
    "/api/cases/export?q=duplicate&priority=High",
  );
});
it("preserves a correction draft when saving returns a conflict", async () => {
  history.replaceState({}, "", "/cases/CQ-ONE");
  vi.mocked(pilot.review).mockRejectedValue(
    new ApiError("Another tab changed this case.", 409),
  );
  render(<App />);
  await screen.findByLabelText("Complaint issue");
  fireEvent.change(screen.getByLabelText("Complaint issue"), {
    target: { value: "Fees or interest" },
  });
  fireEvent.change(screen.getByLabelText("Review reason"), {
    target: { value: "This is a fee." },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm & save review" }),
  );
  await screen.findByText("Another tab changed this case.");
  expect(screen.getByLabelText("Complaint issue")).toHaveValue(
    "Fees or interest",
  );
  expect(screen.getByLabelText("Review reason")).toHaveValue("This is a fee.");
  expect(
    screen.getByRole("button", { name: "Load latest version and keep draft" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Original analysis")).toBeInTheDocument();
});
it("retains a pending correction while a note updates the case revision", async () => {
  history.replaceState({}, "", "/cases/CQ-ONE");
  vi.mocked(pilot.note).mockResolvedValue({ ...item, revision: 2 });
  render(<App />);
  await screen.findByLabelText("Complaint issue");
  fireEvent.change(screen.getByLabelText("Complaint issue"), {
    target: { value: "Fees or interest" },
  });
  fireEvent.change(screen.getByLabelText("Review reason"), {
    target: { value: "Fee evidence" },
  });
  fireEvent.change(screen.getByLabelText("Case note"), {
    target: { value: "Investigation note" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add note" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Case note")).toHaveValue(""),
  );
  expect(screen.getByLabelText("Review reason")).toHaveValue("Fee evidence");
  expect(screen.getByLabelText("Complaint issue")).toHaveValue(
    "Fees or interest",
  );
});
it("requires a confirmed review and reason before resolution", async () => {
  history.replaceState({}, "", "/cases/CQ-ONE");
  vi.mocked(pilot.review).mockResolvedValue({
    ...item,
    revision: 2,
    confirmed: 1,
  });
  render(<App />);
  await screen.findByLabelText("Review reason");
  expect(screen.getByRole("button", { name: "Resolve case" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Resolution / status note"), {
    target: { value: "Resolved after review" },
  });
  expect(screen.getByRole("button", { name: "Resolve case" })).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm & save review" }),
  );
  await screen.findByText("Review saved. Your decision is recorded.");
  expect(screen.getByRole("button", { name: "Resolve case" })).toBeEnabled();
});
it("uses the same idempotency key when retrying a failed submit", async () => {
  history.replaceState({}, "", "/analyze");
  vi.mocked(pilot.submit).mockRejectedValue(
    new Error("Connection interrupted"),
  );
  render(<App />);
  fireEvent.change(screen.getByLabelText("Complaint narrative"), {
    target: { value: "A duplicate charge" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Analyze complaint" }));
  await screen.findByText("Connection interrupted");
  fireEvent.click(screen.getByRole("button", { name: "Analyze complaint" }));
  await waitFor(() => expect(pilot.submit).toHaveBeenCalledTimes(2));
  expect(vi.mocked(pilot.submit).mock.calls[0][1]).toBe(
    vi.mocked(pilot.submit).mock.calls[1][1],
  );
});
it("opens persisted job results after direct navigation", async () => {
  history.replaceState({}, "", "/imports?job=JOB-ONE");
  const job: Job = {
    id: "JOB-ONE",
    source: "import",
    created_at: original.created_at,
    status: "completed_with_errors",
    total: 2,
    counts: { complete: 1, failed: 1, pending: 0, running: 0, cancelled: 0 },
    rows: [
      {
        position: 0,
        text: "Success",
        state: "complete",
        case_id: item.id,
        error: null,
      },
      {
        position: 1,
        text: "Failure",
        state: "failed",
        case_id: "CQ-TWO",
        error: "Model unavailable",
      },
    ],
  };
  vi.mocked(pilot.job).mockResolvedValue(job);
  render(<App />);
  await screen.findByText("1 / 2 saved");
  expect(screen.getByRole("link", { name: "Open CQ-ONE" })).toHaveAttribute(
    "href",
    "/cases/CQ-ONE",
  );
  expect(
    screen.getByRole("button", { name: "Retry failed rows" }),
  ).toBeEnabled();
  expect(screen.getByText("Model unavailable")).toBeInTheDocument();
});
it("keeps cases available when model health fails", async () => {
  vi.mocked(pilot.health).mockRejectedValue(new Error("Offline"));
  render(<App />);
  await screen.findByText("CQ-ONE");
  await screen.findByText("Engine unavailable");
  expect(screen.getByRole("link", { name: "Open CQ-ONE" })).toBeInTheDocument();
});
it("accepts a valid single-column CSV and rejects a missing text header", async () => {
  history.replaceState({}, "", "/imports");
  render(<App />);
  const input = screen.getByLabelText("Upload complaint CSV");
  fireEvent.change(input, {
    target: {
      files: [new File(["wrong\nsample\n"], "bad.csv", { type: "text/csv" })],
    },
  });
  await screen.findByText("The CSV needs a column named text.");
  fireEvent.change(input, {
    target: {
      files: [
        new File(
          [
            'text\n"My credit card was charged twice."\n"My report is incorrect."\n',
          ],
          "valid.csv",
          { type: "text/csv" },
        ),
      ],
    },
  });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Process 2 complaints" }),
    ).toBeEnabled(),
  );
  expect(pilot.submit).not.toHaveBeenCalled();
});
