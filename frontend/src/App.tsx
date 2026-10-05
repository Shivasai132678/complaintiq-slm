import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Database,
  FileUp,
  LayoutDashboard,
  LoaderCircle,
  MessageSquare,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import Papa from "papaparse";
import { ApiError, pilot } from "./pilot-api";
import type {
  Case,
  Config,
  Event,
  Job,
  Overview,
  Page,
  System,
} from "./pilot-api";
import type { Evaluation, Health } from "./types";

const date = (s: string) =>
  new Date(s).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please retry.";

/* Lightweight toast notifications for completed actions. */
type ToastItem = { id: number; text: string };
let pushToast: (text: string) => void = () => {};
const toast = (text: string) => pushToast(text);
function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);
  useEffect(() => {
    let n = 0;
    const timers: ReturnType<typeof setTimeout>[] = [];
    pushToast = (text) => {
      const id = ++n;
      setItems((v) => [...v.slice(-2), { id, text }]);
      timers.push(
        setTimeout(() => setItems((v) => v.filter((x) => x.id !== id)), 3800),
      );
    };
    return () => {
      pushToast = () => {};
      timers.forEach(clearTimeout);
    };
  }, []);
  return (
    <div className="toasts" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className="toast">
          <span className="toast-icon">
            <Check size={14} />
          </span>
          {t.text}
        </div>
      ))}
    </div>
  );
}

const EXAMPLES = [
  {
    label: "Late fee",
    text: "I was charged a $39 late fee on my credit card even though my payment posted two days before the due date. I called customer service twice and they still refuse to refund the fee.",
  },
  {
    label: "Duplicate charge",
    text: "My credit card statement shows the same $120 purchase twice. I disputed the duplicate charge three weeks ago and the bank still has not reversed it.",
  },
  {
    label: "Credit report error",
    text: "My credit report shows a collection account that I never opened. I disputed it with the credit bureau a month ago and the incorrect account is still on my report.",
  },
  {
    label: "Deposit hold",
    text: "I deposited a check into my checking account last week. The bank placed a hold and the money is still not available, even though the check has cleared.",
  },
];
function useRoute() {
  const [url, set] = useState(location.pathname + location.search);
  useEffect(() => {
    const f = () => set(location.pathname + location.search);
    addEventListener("popstate", f);
    return () => removeEventListener("popstate", f);
  }, []);
  return [
    url,
    (path: string) => {
      history.pushState({}, "", path);
      set(path);
      window.scrollTo(0, 0);
    },
  ] as const;
}
type Go = (path: string) => void;
function Link({
  to,
  go,
  children,
  className = "",
}: {
  to: string;
  go: Go;
  children: ReactNode;
  className?: string;
}) {
  return (
    <a
      href={to}
      className={className}
      onClick={(e) => {
        if (!e.metaKey && !e.ctrlKey && !e.shiftKey) {
          e.preventDefault();
          go(to);
        }
      }}
    >
      {children}
    </a>
  );
}
function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function ErrorBox({ text }: { text: string }) {
  return text ? (
    <div className="error" role="alert">
      {text}
    </div>
  ) : null;
}
function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="empty">
      <ClipboardList size={30} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Heading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </header>
  );
}
function Panel({
  title,
  subtitle,
  children,
  action,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={"panel " + className}>
      <header className="panel-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}
function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={20} /> Loading workspace…
    </div>
  );
}
function EventList({ items, go }: { items: Event[]; go?: Go }) {
  return items.length ? (
    <ol className="timeline">
      {items.map((e) => (
        <li key={e.seq}>
          <span className="timeline-dot" />
          <div>
            <div className="event-heading">
              <strong>
                {e.kind === "review"
                  ? "Classification reviewed"
                  : e.kind === "note"
                    ? "Note added"
                    : `${e.detail.from} → ${e.detail.to}`}
              </strong>
              <time>{date(e.at)}</time>
            </div>
            {go && (
              <Link to={"/cases/" + e.case_id} go={go} className="case-link">
                {e.case_id}
              </Link>
            )}
            {e.detail.changes &&
              Object.entries(e.detail.changes).map(([k, v]) => (
                <p key={k}>
                  <b>{k}:</b> {v.from} → {v.to}
                </p>
              ))}
            {(e.detail.note || e.detail.reason) && (
              <p className="preserve">{e.detail.note || e.detail.reason}</p>
            )}
            <small>{e.actor}</small>
          </div>
        </li>
      ))}
    </ol>
  ) : (
    <div className="quiet-empty">
      No review activity yet. Original predictions are preserved.
    </div>
  );
}

export default function App() {
  const [url, go] = useRoute();
  const path = url.split("?")[0];
  const [health, setHealth] = useState<Health | null>(null),
    [checked, setChecked] = useState(false),
    [config, setConfig] = useState<Config | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    pilot
      .config()
      .then((c) => {
        if (active) setConfig(c);
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      });
    const check = async () => {
      try {
        const h = await pilot.health();
        if (active) setHealth(h);
      } catch {
        if (active) setHealth(null);
      } finally {
        if (active) setChecked(true);
      }
    };
    void check();
    const t = setInterval(check, 30000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, []);
  const nav = [
    ["/overview", "Overview", LayoutDashboard],
    ["/cases", "Cases", ClipboardList],
    ["/analyze", "Analyze", Sparkles],
    ["/imports", "Imports", FileUp],
    ["/system", "Model & System", Activity],
  ] as const;
  const activeLabel = nav.find(([p]) => path.startsWith(p))?.[1] ?? "Cases";
  const pageTitle = path.startsWith("/cases/")
    ? decodeURIComponent(path.slice(7))
    : activeLabel;
  useEffect(() => {
    document.title = `${pageTitle} · ComplaintIQ`;
  }, [pageTitle]);
  return (
    <div className="pilot">
      <aside className="sidebar">
        <Link to="/overview" go={go} className="brand">
          <span className="brand-mark">
            cq<span>•</span>
          </span>
          <span>
            ComplaintIQ<small>LOCAL OPERATIONS</small>
          </span>
        </Link>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav.map(([p, label, Icon]) => (
            <Link
              key={p}
              to={p}
              go={go}
              className={
                "nav-link " +
                ((path === "/" && p === "/cases") || path.startsWith(p)
                  ? "active"
                  : "")
              }
            >
              <Icon size={19} />
              <span>{label}</span>
              {((path === "/" && p === "/cases") || path.startsWith(p)) && (
                <ChevronRight size={15} />
              )}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className={"engine-card " + (!health ? "offline" : "")}>
            <span className="engine-light" />
            <strong>
              {health
                ? "Local engine ready"
                : checked
                  ? "Engine unavailable"
                  : "Checking engine"}
            </strong>
            <p>
              {health?.backend === "slm"
                ? "Fine-tuned Qwen2.5 · 1.5B"
                : health
                  ? "Traditional ML baseline"
                  : "Your saved cases remain available."}
            </p>
            <Link to="/system" go={go}>
              View system status <ArrowRight size={13} />
            </Link>
          </div>
          <div className="prepared-for">
            <small>PREPARED FOR</small>
            <img src="/veltris-logo-light.png" alt="Veltris" />
          </div>
          <div className="operator">
            <span>LO</span>
            <div>
              Local operator<small>Single-device workspace</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <div className="topbar">
          <span>
            Workspace <ChevronRight size={14} /> <strong>{activeLabel}</strong>
          </span>
          <div>
            <span className="client-mark">
              <span>ComplaintIQ for</span>
              <img src="/veltris-logo.png" alt="Veltris" />
            </span>
            <span className="topbar-divider" />
            <span className="local-dot" /> On this Mac{" "}
            <span className="avatar">LO</span>
          </div>
        </div>
        <Toaster />
        <main key={path}>
          <ErrorBox text={error} />
          {path === "/overview" ? (
            <OverviewPage go={go} />
          ) : path === "/analyze" ? (
            <Analyze go={go} health={health} />
          ) : path === "/imports" ? (
            <Imports go={go} query={url.split("?")[1] ?? ""} />
          ) : path === "/system" ? (
            <SystemPage health={health} />
          ) : path.startsWith("/cases/") ? (
            config ? (
              <CaseDetail
                id={decodeURIComponent(path.slice(7))}
                config={config}
                go={go}
                fresh={new URLSearchParams(url.split("?")[1] ?? "").has("new")}
              />
            ) : (
              <Loading />
            )
          ) : (
            <Cases go={go} query={url.split("?")[1] ?? ""} config={config} />
          )}
          <footer className="page-footer">
            <span>
              <ShieldCheck size={14} /> Human review is part of every decision.
            </span>
            <span>Private workspace · Stored on this Mac</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
function OverviewPage({ go }: { go: Go }) {
  const [data, setData] = useState<Overview | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    pilot
      .overview()
      .then((v) => {
        if (active) setData(v);
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <>
      <Heading
        eyebrow="YOUR OPERATIONS, IN FOCUS"
        title="A clear view of what needs you."
        description="Review the queue, follow the work, and close the loop."
      >
        <Link to="/analyze" go={go} className="button primary">
          <Plus size={17} /> New analysis
        </Link>
      </Heading>
      <ErrorBox text={error} />
      {data ? (
        <>
          <div className="metrics">
            {[
              [data.unreviewed, "Awaiting confirmation", "/cases?confirmed=0"],
              [
                data.by_status["In review"] ?? 0,
                "In review",
                "/cases?status=In+review",
              ],
              [
                data.by_status.Resolved ?? 0,
                "Resolved",
                "/cases?status=Resolved",
              ],
              [
                data.high_open,
                "High-priority open",
                "/cases?urgent=1&sort=priority",
              ],
            ].map(([n, label, to], i) => (
              <Link
                key={label}
                to={String(to)}
                go={go}
                className={"metric " + (i === 0 ? "featured" : "")}
              >
                <div>
                  {label}
                  <ArrowUp />
                </div>
                <strong>{n}</strong>
                <small>
                  {i === 3
                    ? "High / critical · excludes resolved"
                    : i === 0
                      ? "Open cases · not yet human-confirmed"
                      : "Current saved cases"}
                </small>
              </Link>
            ))}
          </div>
          <div className="overview-grid">
            <Panel
              title="Work moves forward here"
              subtitle="Your current case lifecycle"
              action={
                <Link to="/cases" go={go} className="text-link">
                  Open queue <ArrowRight size={15} />
                </Link>
              }
            >
              <div className="lifecycle">
                {["Queued", "In review", "Resolved"].map((s, i) => (
                  <Link
                    to={"/cases?status=" + encodeURIComponent(s)}
                    go={go}
                    key={s}
                  >
                    <span className="step-number">0{i + 1}</span>
                    <h3>{s}</h3>
                    <strong>{data.by_status[s] ?? 0}</strong>
                    <p>
                      {
                        [
                          "Ready for a first look",
                          "Being investigated",
                          "Reviewed and closed",
                        ][i]
                      }
                    </p>
                  </Link>
                ))}
              </div>
              <div className="panel-foot">
                {data.total} cases in the workspace. Every prediction starts
                unreviewed.
              </div>
            </Panel>
            <Panel
              title="Complaints by product"
              subtitle="Current labels, including reviewer corrections"
            >
              <div className="bars">
                {Object.entries(data.by_product).map(([k, v]) => (
                  <Link
                    to={"/cases?product=" + encodeURIComponent(k)}
                    go={go}
                    key={k}
                  >
                    <div>
                      <span>{k}</span>
                      <strong>{v}</strong>
                    </div>
                    <div className="bar-track">
                      <i
                        style={{
                          width: `${data.total ? (v / data.total) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </Link>
                ))}
              </div>
            </Panel>
          </div>
          <Panel
            title="Recent activity"
            subtitle="The decisions behind the case history"
          >
            <EventList items={data.activity} go={go} />
          </Panel>
        </>
      ) : (
        !error && <Loading />
      )}
    </>
  );
}
function ArrowUp() {
  return <ArrowRight size={16} className="arrow-up" />;
}
function Cases({
  go,
  query,
  config,
}: {
  go: Go;
  query: string;
  config: Config | null;
}) {
  const params = new URLSearchParams(query);
  const [data, setData] = useState<Page | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(true);
  const [search, setSearch] = useState(params.get("q") ?? "");
  useEffect(
    () => setSearch(new URLSearchParams(query).get("q") ?? ""),
    [query],
  );
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError("");
    pilot
      .cases(query)
      .then((v) => {
        if (active) setData(v);
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [query]);
  const change = (k: string, v: string) => {
    const p = new URLSearchParams(query);
    p.delete("page");
    v ? p.set(k, v) : p.delete(k);
    go("/cases?" + p);
  };
  return (
    <>
      <Heading
        eyebrow="CASE WORKSPACE"
        title="Every case. A clear next step."
        description="Review model predictions, capture your decisions, and track cases through resolution."
      >
        <Link to="/analyze" go={go} className="button primary">
          <Plus size={17} /> New case
        </Link>
      </Heading>
      <section className="panel queue-panel">
        <div className="queue-tabs">
          {["All cases", "Queued", "In review", "Resolved"].map((s) => (
            <button
              key={s}
              className={
                (params.get("status") ?? "") === (s === "All cases" ? "" : s)
                  ? "selected"
                  : ""
              }
              onClick={() => change("status", s === "All cases" ? "" : s)}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="filters">
          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              change("q", search);
            }}
          >
            <Search size={17} />
            <input
              aria-label="Search cases"
              placeholder="Search narrative or case ID"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button aria-label="Apply search" type="submit">
              <ArrowRight size={16} />
            </button>
          </form>
          <select
            aria-label="Product filter"
            value={params.get("product") ?? ""}
            onChange={(e) => change("product", e.target.value)}
          >
            <option value="">All products</option>
            {[
              ...Object.keys(config?.taxonomy ?? {}),
              "Outside supported scope",
              "Unknown",
            ].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            aria-label="Priority filter"
            value={params.get("priority") ?? ""}
            onChange={(e) => change("priority", e.target.value)}
          >
            <option value="">All priorities</option>
            {["Critical", "High", "Medium", "Low"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            aria-label="Department filter"
            value={params.get("department") ?? ""}
            onChange={(e) => change("department", e.target.value)}
          >
            <option value="">All departments</option>
            {config?.departments.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </div>
        <div className="filter-secondary">
          <label className="date-field">
            From{" "}
            <input
              type="date"
              aria-label="From date"
              value={params.get("start") ?? ""}
              onChange={(e) => change("start", e.target.value)}
            />
          </label>
          <label className="date-field">
            To{" "}
            <input
              type="date"
              aria-label="To date"
              value={params.get("end") ?? ""}
              onChange={(e) => change("end", e.target.value)}
            />
          </label>
          <select
            aria-label="Review filter"
            value={params.get("confirmed") ?? ""}
            onChange={(e) => change("confirmed", e.target.value)}
          >
            <option value="">All review states</option>
            <option value="0">Unreviewed</option>
            <option value="1">Confirmed</option>
          </select>
          <select
            aria-label="Sort cases"
            value={params.get("sort") ?? "newest"}
            onChange={(e) => change("sort", e.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="priority">Priority first</option>
          </select>
          {query && (
            <Link to="/cases" go={go} className="text-link">
              Clear filters
            </Link>
          )}
          <a
            className="text-link export-link"
            href={"/api/cases/export?" + query}
          >
            <ArrowDownToLine size={15} /> Export filtered
          </a>
        </div>
        <ErrorBox text={error} />
        {busy ? (
          <Loading />
        ) : data?.items.length ? (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Case / narrative</th>
                    <th>Classification</th>
                    <th>Priority</th>
                    <th>Review</th>
                    <th>Status</th>
                    <th>Received</th>
                    <th>
                      <span className="sr-only">Open case</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <Link
                          to={"/cases/" + c.id}
                          go={go}
                          className="case-link"
                        >
                          {c.id}
                        </Link>
                        <p className="narrative-preview">{c.text}</p>
                      </td>
                      <td>
                        <strong>{c.product}</strong>
                        <small>{c.issue}</small>
                      </td>
                      <td>
                        <Badge tone={c.priority.toLowerCase()}>
                          {c.priority}
                        </Badge>
                      </td>
                      <td>
                        <Badge tone={c.confirmed ? "confirmed" : "neutral"}>
                          {c.confirmed ? "Confirmed" : "Unreviewed"}
                        </Badge>
                      </td>
                      <td>
                        <span className="status-label">{c.status}</span>
                      </td>
                      <td className="date-cell">{date(c.created_at)}</td>
                      <td>
                        <Link
                          to={"/cases/" + c.id}
                          go={go}
                          className="icon-button"
                        >
                          <span className="sr-only">Open {c.id}</span>
                          <ArrowRight size={17} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {data.total} matching cases · Page {data.page} of{" "}
                {Math.max(1, Math.ceil(data.total / data.page_size))}
              </span>
              <div>
                {[-1, 1].map((delta) => (
                  <button
                    key={delta}
                    aria-label={delta < 0 ? "Previous page" : "Next page"}
                    disabled={
                      delta < 0
                        ? data.page === 1
                        : data.page * data.page_size >= data.total
                    }
                    onClick={() => {
                      const p = new URLSearchParams(query);
                      p.set("page", String(data.page + delta));
                      go("/cases?" + p);
                    }}
                  >
                    {delta < 0 ? (
                      <ChevronLeft size={17} />
                    ) : (
                      <ChevronRight size={17} />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </>
        ) : (
          <Empty title="No cases to show">
            Try different filters or analyze your first complaint.
          </Empty>
        )}
      </section>
    </>
  );
}
function CaseDetail({
  id,
  config,
  go,
  fresh = false,
}: {
  id: string;
  config: Config;
  go: Go;
  fresh?: boolean;
}) {
  const [item, setItem] = useState<Case | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    pilot
      .case(id)
      .then((c) => {
        if (!active) return;
        setItem(c);
        if (fresh)
          toast(
            `${c.id} created · classified in ${(c.original.latency_ms / 1000).toFixed(2)}s`,
          );
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      });
    return () => {
      active = false;
    };
  }, [id]);
  return (
    <>
      <Link to="/cases" go={go} className="back-link">
        <ArrowLeft size={16} /> Back to cases
      </Link>
      <ErrorBox text={error} />
      {item ? (
        <>
          <Heading
            eyebrow={"CASE " + id}
            title={item.product}
            description={`Received ${date(item.created_at)} · ${item.confirmed ? "Human-confirmed" : "Awaiting human confirmation"}`}
          >
            <Badge tone={item.status === "Resolved" ? "confirmed" : "neutral"}>
              {item.status}
            </Badge>
          </Heading>
          <div className={"case-layout" + (fresh ? " reveal" : "")}>
            <div>
              <Panel
                title="The customer's words"
                subtitle="Original narrative · preserved as received"
              >
                <div className="narrative-full">{item.text}</div>
                {item.original.input_truncated && (
                  <div className="notice">
                    The model used the first{" "}
                    {item.original.input_chars_used?.toLocaleString()}{" "}
                    normalized characters. Review the full narrative before
                    confirming.
                  </div>
                )}
                <div className="panel-foot">
                  {item.text.length.toLocaleString()} characters ·{" "}
                  {item.original.backend === "slm" ? "Local SLM" : "Baseline"} ·{" "}
                  {(item.original.latency_ms / 1000).toFixed(2)}s{" "}
                  {item.original.cached ? "(cached)" : ""}
                </div>
              </Panel>
              <Panel
                title="Original analysis"
                subtitle="Immutable model prediction and policy assessment"
                className="analysis-panel"
                action={
                  fresh ? (
                    <span className="fresh-badge">
                      <Sparkles size={13} /> Just analyzed ·{" "}
                      {(item.original.latency_ms / 1000).toFixed(2)}s
                    </span>
                  ) : undefined
                }
              >
                <div className="original-analysis">
                  <div className="eyebrow">MODEL PREDICTION</div>
                  <h3>{item.original.product}</h3>
                  <p>{item.original.issue}</p>
                  <code>{item.original.model_version}</code>
                  <div className="divider" />
                  <div className="eyebrow">WORKFLOW POLICY</div>
                  <div className="inline">
                    <Badge tone={item.original.priority.toLowerCase()}>
                      {item.original.priority}
                    </Badge>
                    <span>{item.original.department}</span>
                  </div>
                  <p>{item.original.priority_reason}</p>
                  <p>{item.original.action}</p>
                  {!!item.review_flag && (
                    <div className="notice">
                      This case was originally flagged for human review.
                    </div>
                  )}
                </div>
              </Panel>
            </div>
            <div>
              <ReviewForm item={item} config={config} saved={setItem} />
              <Lifecycle item={item} saved={setItem} />
            </div>
          </div>
          <div className="case-layout">
            <Notes item={item} saved={setItem} />
            <Panel
              title="Case history"
              subtitle="Append-only changes · original analysis remains intact"
            >
              <EventList items={item.events ?? []} />
            </Panel>
          </div>
        </>
      ) : (
        !error && <Loading />
      )}
    </>
  );
}
function ReviewForm({
  item,
  config,
  saved,
}: {
  item: Case;
  config: Config;
  saved: (c: Case) => void;
}) {
  const initial = () => ({
    product: item.product,
    issue: item.issue,
    priority: item.priority,
    department: item.department,
  });
  const [form, setForm] = useState(initial),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [conflict, setConflict] = useState(false);
  useEffect(() => {
    setForm(initial());
    setReason("");
  }, [item.id]);
  const outside = form.product === config.outside;
  const issues = outside
    ? [config.outside]
    : (config.taxonomy[form.product] ?? []);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const c = await pilot.review(item.id, {
        ...form,
        reason,
        revision: item.revision,
      });
      saved(c);
      setReason("");
      setMessage("Review saved. Your decision is recorded.");
      toast(
        c.product === item.product && c.issue === item.issue
          ? "Classification confirmed"
          : "Correction recorded in case history",
      );
      setConflict(false);
    } catch (e) {
      setError(errorText(e));
      setConflict(e instanceof ApiError && e.status === 409);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel
      title="Your review"
      subtitle="Confirm the prediction or make a correction"
      action={<ShieldCheck size={20} />}
    >
      <form className="form-pad" onSubmit={submit}>
        <ErrorBox text={error} />
        {message && (
          <div className="success" role="status">
            <Check size={16} />
            {message}
          </div>
        )}
        {conflict && (
          <button
            type="button"
            className="button"
            onClick={async () => {
              try {
                const c = await pilot.case(item.id);
                saved(c);
                setConflict(false);
                setError(
                  "Latest version loaded. Check your draft against the case history before saving.",
                );
              } catch (e) {
                setError(errorText(e));
              }
            }}
          >
            Load latest version and keep draft
          </button>
        )}
        <fieldset disabled={busy || item.status === "Resolved"}>
          <label>
            Financial product
            <select
              value={form.product}
              onChange={(e) => {
                const p = e.target.value;
                setForm({
                  ...form,
                  product: p,
                  issue:
                    p === config.outside
                      ? config.outside
                      : (config.taxonomy[p]?.[0] ?? ""),
                  department: config.routing[p] ?? "Manual Review Team",
                });
              }}
            >
              {!config.taxonomy[form.product] && !outside && (
                <option value={form.product}>
                  {form.product} — choose a review outcome
                </option>
              )}
              {Object.keys(config.taxonomy).map((v) => (
                <option key={v}>{v}</option>
              ))}
              <option>{config.outside}</option>
            </select>
          </label>
          <label>
            Complaint issue
            <select
              value={form.issue}
              onChange={(e) => setForm({ ...form, issue: e.target.value })}
            >
              {!issues.includes(form.issue) && (
                <option value={form.issue}>
                  {form.issue} — select an issue
                </option>
              )}
              {issues.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <div className="form-row">
            <label>
              Priority
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              >
                {["Low", "Medium", "High", "Critical"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Route to
              <select
                value={form.department}
                onChange={(e) =>
                  setForm({ ...form, department: e.target.value })
                }
              >
                {config.departments.map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </div>
          <small className="field-help">
            Changing the product suggests a department. Confirm the route before
            saving.
          </small>
          <label>
            Review reason
            <textarea
              rows={3}
              maxLength={4000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Required when changing the classification, priority, or department."
            />
          </label>
          <button
            className="button primary wide"
            disabled={!issues.includes(form.issue)}
          >
            {busy ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              <Check size={17} />
            )}{" "}
            Confirm & save review
          </button>
        </fieldset>
        {item.status === "Resolved" && (
          <p className="field-help">Reopen this case to change its review.</p>
        )}
      </form>
    </Panel>
  );
}
function Lifecycle({ item, saved }: { item: Case; saved: (c: Case) => void }) {
  const [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const change = async (status: string) => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      saved(
        await pilot.transition(item.id, {
          revision: item.revision,
          status,
          reason,
        }),
      );
      toast(
        status === "Resolved"
          ? "Case resolved"
          : item.status === "Resolved"
            ? "Case reopened for review"
            : `Moved to ${status.toLowerCase()}`,
      );
      setReason("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel
      title="Move the case forward"
      subtitle="A resolution always needs a confirmed review"
    >
      <div className="form-pad">
        <ErrorBox text={error} />
        <label>
          {item.status === "Resolved"
            ? "Reopening reason"
            : "Resolution / status note"}
          <textarea
            rows={2}
            maxLength={4000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={
              item.status === "Resolved"
                ? "Why does this need another look?"
                : "Record the outcome or the next step."
            }
          />
        </label>
        <div className="actions">
          {item.status === "Resolved" ? (
            <button
              className="button"
              disabled={busy || !reason.trim()}
              onClick={() => change("In review")}
            >
              Reopen case
            </button>
          ) : (
            <>
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  change(item.status === "Queued" ? "In review" : "Queued")
                }
              >
                {item.status === "Queued" ? "Start review" : "Return to queue"}
              </button>
              <button
                className="button primary"
                disabled={busy || !item.confirmed || !reason.trim()}
                onClick={() => change("Resolved")}
              >
                <Check size={16} /> Resolve case
              </button>
            </>
          )}
        </div>
        {!item.confirmed && (
          <small className="field-help">
            Confirm the classification before resolving.
          </small>
        )}
      </div>
    </Panel>
  );
}
function Notes({ item, saved }: { item: Case; saved: (c: Case) => void }) {
  const [note, setNote] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <Panel
      title="Add context"
      subtitle="Notes are preserved in the case history"
    >
      <form
        className="form-pad"
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy) return;
          setBusy(true);
          setError("");
          try {
            saved(
              await pilot.note(item.id, {
                revision: item.revision,
                reason: note,
              }),
            );
            toast("Note added to case history");
            setNote("");
          } catch (e) {
            setError(errorText(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        <ErrorBox text={error} />
        <label>
          Case note
          <textarea
            rows={4}
            maxLength={4000}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add investigation details or a handover note."
          />
        </label>
        <button className="button" disabled={busy || !note.trim()}>
          <MessageSquare size={16} /> Add note
        </button>
      </form>
    </Panel>
  );
}
function Analyze({ go, health }: { go: Go; health: Health | null }) {
  const [text, setText] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const requestKey = useRef(crypto.randomUUID()),
    pending = useRef(false);
  return (
    <>
      <Heading
        eyebrow="LOCAL INTELLIGENCE"
        title="Start with the customer's story."
        description="A model prediction is the first step. Your review makes it actionable."
      />
      <div className="analysis-layout">
        <Panel title="New complaint" subtitle="Paste the original narrative">
          <form
            className="form-pad"
            onSubmit={async (e) => {
              e.preventDefault();
              if (pending.current) return;
              pending.current = true;
              setBusy(true);
              setError("");
              try {
                const j = await pilot.submit(
                  [text],
                  requestKey.current,
                  "analysis",
                );
                go("/imports?job=" + j.id);
              } catch (e) {
                setError(errorText(e));
              } finally {
                pending.current = false;
                setBusy(false);
              }
            }}
          >
            <ErrorBox text={error} />
            <div
              className="examples"
              role="group"
              aria-label="Example complaints"
            >
              <span>Try an example</span>
              {EXAMPLES.map((x) => (
                <button
                  type="button"
                  key={x.label}
                  className={
                    "example-chip" + (text === x.text ? " selected" : "")
                  }
                  disabled={busy}
                  onClick={() => {
                    setText(x.text);
                    requestKey.current = crypto.randomUUID();
                  }}
                >
                  {x.label}
                </button>
              ))}
            </div>
            <label>
              Complaint narrative
              <textarea
                className="analysis-input"
                maxLength={6000}
                rows={12}
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  requestKey.current = crypto.randomUUID();
                }}
                placeholder="For example: My credit card statement includes a duplicate charge. I disputed it, but the extra charge has not been reversed…"
                disabled={busy}
              />
            </label>
            <div className="input-meta">
              <span>{text.length.toLocaleString()} / 6,000 characters</span>
              <span>Model reads first 2,000 normalized characters</span>
            </div>
            {!health && (
              <div className="notice">
                The engine is not confirmed ready. You can submit work; if
                inference fails, retry it from Imports when the engine returns.
              </div>
            )}
            <button className="button primary" disabled={busy || !text.trim()}>
              {busy ? (
                <LoaderCircle size={17} className="spin" />
              ) : (
                <Sparkles size={17} />
              )}{" "}
              Analyze complaint <ArrowRight size={17} />
            </button>
          </form>
        </Panel>
        <div>
          <section className="explainer">
            <div className="eyebrow">A CLEAR DIVISION OF WORK</div>
            <h2>
              Intelligence.
              <br />
              With accountability.
            </h2>
            <div>
              <span>01</span>
              <h3>Model classification</h3>
              <p>
                Product and issue, predicted by the configured local engine.
              </p>
            </div>
            <div>
              <span>02</span>
              <h3>Workflow policies</h3>
              <p>Priority and routing suggestions, with an explicit reason.</p>
            </div>
            <div>
              <span>03</span>
              <h3>Your decision</h3>
              <p>
                Confirm or correct the case. Every change stays in its history.
              </p>
            </div>
          </section>
          <div className="privacy-note">
            <ShieldCheck size={20} />
            <p>
              Inference and case storage stay on this Mac. No external AI
              service receives the narrative.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
function Imports({ go, query }: { go: Go; query: string }) {
  const selected = new URLSearchParams(query).get("job");
  const [jobs, setJobs] = useState<Job[]>([]),
    [current, setCurrent] = useState<Job | null>(null),
    [texts, setTexts] = useState<string[]>([]),
    [name, setName] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false),
    [dragging, setDragging] = useState(false);
  const key = useRef(crypto.randomUUID());
  const pending = useRef(false);
  const navigating = useRef(false);
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [v, j] = await Promise.all([
          pilot.jobs(),
          selected ? pilot.job(selected) : Promise.resolve(null),
        ]);
        if (active) {
          setJobs(v.items);
          setCurrent(j);
          setLoaded(true);
          if (
            j?.source === "analysis" &&
            j.status === "complete" &&
            !navigating.current
          ) {
            navigating.current = true;
            go("/cases/" + j.rows[0].case_id + "?new=1");
          }
        }
      } catch (e) {
        if (active) setError(errorText(e));
      }
    };
    void load();
    const t = setInterval(load, selected ? 500 : 1500);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, [selected]);
  const upload = (file: File | undefined) => {
    setError("");
    setTexts([]);
    if (!file) return;
    setName(file.name);
    key.current = crypto.randomUUID();
    if (file.size > 2 * 1024 * 1024) {
      setError("Choose a CSV no larger than 2 MB.");
      return;
    }
    Papa.parse<{ text?: string }>(file, {
      delimiter: ",",
      header: true,
      skipEmptyLines: "greedy",
      complete: (r) => {
        if (!r.meta.fields?.includes("text")) {
          setError("The CSV needs a column named text.");
          return;
        }
        const rows = r.data.map((v) => v.text?.trim() ?? "");
        if (
          r.errors.length ||
          !rows.length ||
          rows.length > 100 ||
          rows.some((t) => !t || t.length > 6000)
        ) {
          setError(
            "Use 1–100 valid rows with 1–6,000 characters in each text field. Check CSV quoting.",
          );
          return;
        }
        setTexts(rows);
      },
      error: () => setError("This CSV could not be read."),
    });
  };
  const jobAction = async (action: string) => {
    if (!current || busy) return;
    setBusy(true);
    try {
      setCurrent(await pilot.control(current.id, action));
      setError("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      {current?.source === "analysis" && selected ? (
        <Heading
          eyebrow="LOCAL INTELLIGENCE"
          title="Reading the customer's story."
          description="The model runs on this Mac. Your case opens as soon as it is saved."
        />
      ) : (
        <Heading
          eyebrow="DURABLE PROCESSING"
          title={
            selected ? "Follow every row." : "Bring the whole queue together."
          }
          description="One local inference at a time. Progress is saved, even when you close this page."
        />
      )}
      {selected && (
        <Link to="/imports" go={go} className="back-link">
          <ArrowLeft size={16} /> All imports
        </Link>
      )}
      <ErrorBox text={error} />
      {selected ? (
        current &&
        current.source === "analysis" &&
        ["queued", "running", "complete"].includes(current.status) ? (
          <AnalysisProgress job={current} />
        ) : current ? (
          <Panel
            title={current.id}
            subtitle={`${current.total} complaints · ${date(current.created_at)}`}
            action={
              <Badge
                tone={current.status === "complete" ? "confirmed" : "neutral"}
              >
                {current.status.replaceAll("_", " ")}
              </Badge>
            }
          >
            <div className="job-summary">
              <strong>
                {current.counts.complete} / {current.total} saved
              </strong>
              <span>
                {current.counts.failed} failed · {current.counts.pending}{" "}
                pending · {current.counts.cancelled} cancelled
              </span>
              <progress
                max={current.total}
                value={
                  current.counts.complete +
                  current.counts.failed +
                  current.counts.cancelled
                }
              />
              <div className="actions">
                {["queued", "running"].includes(current.status) && (
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() => jobAction("cancel")}
                  >
                    <X size={16} /> Cancel pending
                  </button>
                )}
                {current.counts.failed > 0 && (
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() => jobAction("retry")}
                  >
                    Retry failed rows
                  </button>
                )}
              </div>
              <small>
                Cancellation allows an active row to finish. Retries keep
                successful cases intact.
              </small>
            </div>
            <div className="job-rows">
              {current.rows.map((r) => (
                <div key={r.position}>
                  <span className="step-number">
                    {String(r.position + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p>{r.text}</p>
                    {r.error && <small className="error-text">{r.error}</small>}
                    {r.state === "complete" && (
                      <Link
                        to={"/cases/" + r.case_id}
                        go={go}
                        className="case-link"
                      >
                        Open {r.case_id} <ArrowRight size={13} />
                      </Link>
                    )}
                  </div>
                  <Badge
                    tone={
                      r.state === "complete"
                        ? "confirmed"
                        : r.state === "failed"
                          ? "high"
                          : "neutral"
                    }
                  >
                    {r.state}
                  </Badge>
                </div>
              ))}
            </div>
          </Panel>
        ) : (
          <Loading />
        )
      ) : (
        <>
          <div className="imports-layout">
            <Panel
              title="Import a CSV"
              subtitle="Up to 100 complaints · 2 MB maximum"
            >
              <div className="form-pad">
                <label
                  className={
                    "upload" +
                    (dragging ? " dragging" : "") +
                    (texts.length ? " ready" : "")
                  }
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    if (!busy) upload(e.dataTransfer.files?.[0]);
                  }}
                >
                  <span className="upload-icon">
                    {texts.length ? <Check size={24} /> : <FileUp size={24} />}
                  </span>
                  <strong>
                    {texts.length
                      ? `${name} · ${texts.length} complaints ready`
                      : name || "Drop your complaint CSV here"}
                  </strong>
                  <span>
                    {texts.length
                      ? "Review the preview, then start processing"
                      : "or browse your files · include a column named text"}
                  </span>
                  <span className="button upload-button">Browse files</span>
                  <input
                    aria-label="Upload complaint CSV"
                    className="visually-hidden"
                    type="file"
                    accept=".csv,text/csv"
                    disabled={busy}
                    onChange={(e) => upload(e.target.files?.[0])}
                  />
                </label>
                <button
                  type="button"
                  className="text-link sample-link"
                  onClick={() => {
                    const csv =
                      "text\n" +
                      EXAMPLES.map(
                        (x) => `"${x.text.replaceAll('"', '""')}"`,
                      ).join("\n") +
                      "\n";
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(
                      new Blob([csv], { type: "text/csv" }),
                    );
                    a.download = "complaintiq-sample.csv";
                    a.click();
                    URL.revokeObjectURL(a.href);
                  }}
                >
                  <ArrowDownToLine size={14} /> Download a sample CSV
                </button>
                <p className="field-help">
                  Quoted commas and multiline narratives are supported. Each
                  complaint can contain up to 6,000 characters; the model reads
                  the first 2,000 normalized characters.
                </p>
                <button
                  className="button primary wide"
                  disabled={busy || !texts.length}
                  onClick={async () => {
                    if (pending.current) return;
                    pending.current = true;
                    setBusy(true);
                    setError("");
                    try {
                      const j = await pilot.submit(
                        texts,
                        key.current,
                        "import",
                      );
                      go("/imports?job=" + j.id);
                      setTexts([]);
                    } catch (e) {
                      setError(errorText(e));
                    } finally {
                      pending.current = false;
                      setBusy(false);
                    }
                  }}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <Sparkles size={17} />
                  )}{" "}
                  Process {texts.length || ""} complaints
                </button>
              </div>
            </Panel>
            <Panel
              title="Preview before processing"
              subtitle="Nothing is submitted until you start"
            >
              {texts.length ? (
                <div className="preview-list">
                  {texts.map((t, i) => (
                    <div key={i}>
                      <span>{String(i + 1).padStart(2, "0")}</span>
                      <p>{t}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty title="Your preview will appear here">
                  Choose a CSV to validate its structure and inspect the
                  narratives.
                </Empty>
              )}
            </Panel>
          </div>
          <Panel
            title="Processing history"
            subtitle="Resume, inspect, or retry work from here"
          >
            {!loaded ? (
              <Loading />
            ) : jobs.length ? (
              <div className="import-history">
                {jobs.map((j) => (
                  <Link key={j.id} to={"/imports?job=" + j.id} go={go}>
                    <FileUp size={18} />
                    <div>
                      <strong>{j.id}</strong>
                      <small>
                        {date(j.created_at)} ·{" "}
                        {j.source === "analysis"
                          ? "Single analysis"
                          : "CSV import"}{" "}
                        · {j.counts.complete}/{j.total} saved
                      </small>
                    </div>
                    <Badge
                      tone={j.status === "complete" ? "confirmed" : "neutral"}
                    >
                      {j.status.replaceAll("_", " ")}
                    </Badge>
                    <ArrowRight size={16} />
                  </Link>
                ))}
              </div>
            ) : (
              <Empty title="No processing jobs yet">
                New analyses and imports will appear here.
              </Empty>
            )}
          </Panel>
        </>
      )}
    </>
  );
}
function AnalysisProgress({ job }: { job: Job }) {
  const started = useRef(Date.now());
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(t);
  }, []);
  const stage =
    job.status === "complete" ? 3 : job.status === "running" ? 1 : 0;
  const steps = [
    ["Saved to the local queue", "Durable before inference starts"],
    [
      "Classifying product & issue",
      "Fine-tuned Qwen2.5 · first 2,000 characters",
    ],
    ["Applying workflow policy", "Priority, routing reason and next step"],
    ["Opening your case", "Original prediction stored unchanged"],
  ];
  return (
    <section className="panel analysis-progress" aria-live="polite">
      <div className="progress-head">
        <span className="progress-orb">
          <Sparkles size={22} />
        </span>
        <div>
          <h2>{stage === 3 ? "Case ready" : "Analyzing on this Mac"}</h2>
          <p>
            {job.id} · {((now - started.current) / 1000).toFixed(1)}s
          </p>
        </div>
      </div>
      <p className="progress-text">{job.rows[0]?.text}</p>
      <ol className="progress-steps">
        {steps.map(([title, detail], i) => {
          const state =
            i < stage || stage === 3
              ? "done"
              : i === stage || (stage === 1 && i === 2)
                ? "active"
                : "";
          return (
            <li key={title} className={state}>
              <span className="step-icon">
                {state === "done" ? (
                  <Check size={14} />
                ) : state === "active" ? (
                  <LoaderCircle size={14} className="spin" />
                ) : (
                  String(i + 1)
                )}
              </span>
              <div>
                <strong>{title}</strong>
                <small>{detail}</small>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
function SystemPage({ health }: { health: Health | null }) {
  const [system, setSystem] = useState<System | null>(null),
    [report, setReport] = useState<Evaluation | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [evalError, setEvalError] = useState("");
  useEffect(() => {
    let active = true;
    const load = () =>
      pilot
        .system()
        .then((s) => {
          if (active) setSystem(s);
        })
        .catch((e) => {
          if (active) setError(errorText(e));
        });
    void load();
    pilot
      .evaluation()
      .then((v) => {
        if (active) setReport(v);
      })
      .catch((e) => {
        if (active) setEvalError(errorText(e));
      });
    const t = setInterval(load, 10000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, []);
  return (
    <>
      <Heading
        eyebrow="MODEL & SYSTEM"
        title="Know exactly what's running."
        description="The model, the evidence, and the tools to keep this workspace recoverable."
      />
      <ErrorBox text={error} />
      {notice && (
        <div className="success" role="status">
          <Check size={16} />
          {notice}
        </div>
      )}
      <div className="system-grid">
        <Panel
          title="Active classification engine"
          subtitle="Availability is checked every 30 seconds"
          action={
            <Badge tone={health ? "confirmed" : "high"}>
              {health ? "Connected" : "Unavailable"}
            </Badge>
          }
        >
          <div className="model-hero">
            <span className="model-symbol">
              <Sparkles size={28} />
            </span>
            <div>
              <div className="eyebrow">
                {health?.backend === "slm"
                  ? "FINE-TUNED LOCAL SLM"
                  : health
                    ? "TRADITIONAL ML BASELINE"
                    : "MODEL CONNECTION"}
              </div>
              <h2>
                {health?.backend === "slm"
                  ? "Qwen2.5 · 1.5B"
                  : health
                    ? "TF-IDF classifier"
                    : "Waiting for the local engine"}
              </h2>
              <p>Product and issue classification · Human review required</p>
            </div>
          </div>
          <dl className="facts">
            <div>
              <dt>Loaded model</dt>
              <dd>
                <code>{health?.model_version ?? "Not confirmed"}</code>
              </dd>
            </div>
            <div>
              <dt>Training examples</dt>
              <dd>{health?.training_size?.toLocaleString() ?? "—"}</dd>
            </div>
            <div>
              <dt>Execution</dt>
              <dd>Local process on this Mac</dd>
            </div>
            <div>
              <dt>Input policy</dt>
              <dd>First 2,000 normalized characters</dd>
            </div>
          </dl>
          <div className="panel-foot">
            Priority and routing use explicit policies. Original predictions
            remain attached to each case.
          </div>
        </Panel>
        <Panel
          title="Workspace health"
          subtitle="Storage and processing are independent of model availability"
        >
          <div className="system-stats">
            <div>
              <Database size={18} />
              <span>Local database</span>
              <strong>
                {system
                  ? (system.database_bytes / 1024 / 1024).toFixed(2) + " MB"
                  : "…"}
              </strong>
            </div>
            <div>
              <LoaderCircle size={18} />
              <span>Pending / running</span>
              <strong>
                {system
                  ? `${system.pending_rows} / ${system.running_rows}`
                  : "…"}
              </strong>
            </div>
            <div>
              <Activity size={18} />
              <span>Failed rows</span>
              <strong>{system?.failed_rows ?? "…"}</strong>
            </div>
            <div>
              <ShieldCheck size={18} />
              <span>Storage schema</span>
              <strong>v{system?.schema_version ?? "…"}</strong>
            </div>
          </div>
          <div className="panel-foot">
            Local operator · localhost only. Saved cases remain readable when
            the model is offline.
          </div>
        </Panel>
      </div>
      <Panel
        title="Measured model performance"
        subtitle="Held-out evaluation, separate from live case statistics"
        action={
          <a
            className="text-link"
            href="/api/evaluation"
            download="evaluation.json"
          >
            <ArrowDownToLine size={15} /> Evaluation JSON
          </a>
        }
      >
        {report ? (
          <>
            <div className="evidence-metrics">
              <div>
                <span>Product accuracy</span>
                <strong>
                  {(report.product.accuracy * 100).toFixed(1)}
                  <small>%</small>
                </strong>
              </div>
              <div>
                <span>Joint accuracy</span>
                <strong>
                  {(report.joint_accuracy * 100).toFixed(1)}
                  <small>%</small>
                </strong>
              </div>
              <div>
                <span>Issue macro F1</span>
                <strong>{report.issue.f1_macro.toFixed(3)}</strong>
              </div>
              <div>
                <span>Held-out complaints</span>
                <strong>{report.test_size}</strong>
              </div>
            </div>
            <div className="panel-foot">
              <strong>Evaluation model: {report.model}</strong>
              <p>
                {Array.isArray(report.limitations)
                  ? report.limitations.join(" ")
                  : report.limitations}
              </p>
            </div>
          </>
        ) : (
          <div className="form-pad">
            <ErrorBox text={evalError} />
            {!evalError && <Loading />}
          </div>
        )}
      </Panel>
      <div className="system-grid">
        <Panel
          title="Backups & recovery"
          subtitle="Automatic daily startup backups · latest seven retained"
        >
          <div className="form-pad">
            <button
              className="button primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const b = await pilot.backup();
                  setNotice("Backup created: " + b.name);
                  toast("Backup created");
                  setSystem(await pilot.system());
                } catch (e) {
                  setError(errorText(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Database size={16} />{" "}
              {busy ? "Creating backup…" : "Create backup now"}
            </button>
            <p className="field-help">
              Backups contain complaint narratives. Keep this Mac and its
              backups under your control. Restore with the documented
              maintenance command while the app is stopped.
            </p>
            <div className="backup-list">
              {system?.backups.slice(0, 5).map((b) => (
                <div key={b.name}>
                  <code>{b.name}</code>
                  <small>{(b.bytes / 1024).toFixed(0)} KB</small>
                </div>
              ))}
            </div>
          </div>
        </Panel>
        <Panel
          title="Reviewed data, ready for improvement"
          subtitle="Turn explicit human decisions into an auditable dataset"
        >
          <div className="form-pad">
            <p>
              Export only confirmed product and issue labels. Cases marked
              outside supported scope are excluded. Original model predictions
              remain preserved in the workspace.
            </p>
            <a href="/api/cases/export?kind=reviewed" className="button">
              <ArrowDownToLine size={16} /> Export reviewed labels
            </a>
            <div className="notice">
              Exporting does not retrain the model. Keep future evaluation data
              separate from training data.
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}
