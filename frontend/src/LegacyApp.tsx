import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileUp,
  Layers3,
  LayoutDashboard,
  Menu,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import Papa from "papaparse";
import { api } from "./api";
import type {
  Analytics,
  BatchResult,
  Complaint,
  Evaluation,
  Health,
} from "./types";
import { Bars, CaseTable, Drawer, Empty, Priority, Result } from "./components";
type View =
  "Overview" | "Analyze" | "Cases" | "Batch upload" | "Model evidence";
const NAV = [
  { name: "Overview" as View, icon: LayoutDashboard },
  { name: "Analyze" as View, icon: Sparkles },
  { name: "Cases" as View, icon: ClipboardList },
  { name: "Batch upload" as View, icon: FileUp },
  { name: "Model evidence" as View, icon: BarChart3 },
];
const emptyAnalytics: Analytics = {
  total: 0,
  by_product: {},
  by_priority: {},
  by_department: {},
  by_backend: {},
  needs_review: 0,
  average_latency_ms: 0,
};
const examples = [
  {
    label: "Credit report dispute",
    text: "My credit report contains a credit card account that is not mine. I disputed the incorrect information twice, but the credit reporting company has not corrected my report.",
  },
  {
    label: "Unexpected bank fee",
    text: "My bank charged an overdraft fee on my checking account even though I had enough money. Customer service promised to reverse the fee, but it remains on my statement.",
  },
  {
    label: "Unauthorized card charge",
    text: "I found an unauthorized charge on my credit card statement. I reported the transaction immediately but the card company refused to investigate the disputed amount.",
  },
];
function download(filename: string, content: string, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
function exportCases(items: Complaint[]) {
  download(
    "complaintiq-cases.csv",
    Papa.unparse(
      items.map((item) => ({
        id: item.id,
        text: item.text,
        product: item.product,
        issue: item.issue,
        priority: item.priority,
        department: item.department,
        status: item.status,
        created_at: item.created_at,
      })),
      { escapeFormulae: true },
    ),
  );
}
function message(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
export default function App() {
  const [view, setView] = useState<View>("Overview");
  const [items, setItems] = useState<Complaint[]>([]);
  const [analytics, setAnalytics] = useState<Analytics>(emptyAnalytics);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [sidebar, setSidebar] = useState(false);
  const refreshSequence = useRef(0);
  const closeDrawer = useCallback(() => setSelected(null), []);
  const refresh = useCallback(async () => {
    const sequence = ++refreshSequence.current;
    setLoading(true);
    setError("");
    try {
      const [cases, summary, engine] = await Promise.all([
        api.complaints(),
        api.analytics(),
        api.health(),
      ]);
      if (sequence !== refreshSequence.current) return;
      setItems(cases.items);
      setAnalytics(summary);
      setHealth(engine);
    } catch (e) {
      if (sequence === refreshSequence.current) {
        setError(message(e));
        setHealth(null);
      }
    } finally {
      if (sequence === refreshSequence.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    let active = true;
    const timer = window.setInterval(() => {
      api
        .health()
        .then((engine) => {
          if (active) setHealth(engine);
        })
        .catch(() => {
          if (active) setHealth(null);
        });
    }, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);
  function navigate(next: View) {
    setView(next);
    setSidebar(false);
    setSelected(null);
  }
  return (
    <div className="workspace">
      <aside className={`sidebar ${sidebar ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault();
            navigate("Overview");
          }}
        >
          <span className="brand-icon">
            CQ
            <span />
          </span>
          <span>
            ComplaintIQ<small>OPERATIONS WORKSPACE</small>
          </span>
        </a>
        <button
          className="mobile-close icon-button"
          aria-label="Close navigation"
          onClick={() => setSidebar(false)}
        >
          <X size={20} />
        </button>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {NAV.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={view === name ? "active" : ""}
              onClick={() => navigate(name)}
              aria-current={view === name ? "page" : undefined}
            >
              <Icon size={19} />
              <span>{name}</span>
              {name === "Cases" ? <small>{analytics.total}</small> : null}
              {view === name ? (
                <ChevronRight size={15} className="nav-chevron" />
              ) : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="engine-card">
            <span className="live-indicator" />
            {health?.backend === "slm"
              ? "FINE-TUNED SLM"
              : health
                ? "BASELINE ENGINE"
                : "ENGINE CONNECTION"}
            <strong>
              {loading
                ? "Connecting to engine"
                : error || !health
                  ? "Connection needs attention"
                  : "Ready for analysis"}
            </strong>
            <p>
              {health?.backend === "slm"
                ? "Qwen2.5 · 1.5B · Local inference"
                : health
                  ? "TF-IDF + Logistic Regression"
                  : "No active engine confirmed"}
            </p>
          </div>
          <div className="sidebar-foot">
            <span className="avatar">CQ</span>
            <div>
              Local workspace<small>Assignment demonstration</small>
            </div>
          </div>
        </div>
      </aside>
      {sidebar ? (
        <button
          className="mobile-shade"
          aria-label="Close navigation"
          onClick={() => setSidebar(false)}
        />
      ) : null}
      <div className="main">
        <header className="topbar">
          <div>
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              onClick={() => setSidebar(true)}
            >
              <Menu size={21} />
            </button>
            <span className="breadcrumb">
              Workspace <ChevronRight size={13} /> <strong>{view}</strong>
            </span>
          </div>
          <div className="topbar-right">
            <span className="local-pill">
              <span />
              Local session
            </span>
            <span className="topbar-divider" />
            <span className="avatar pale">CQ</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="overline">FINANCIAL COMPLAINT INTELLIGENCE</div>
              <h1>
                {view === "Overview"
                  ? "Operations overview"
                  : view === "Analyze"
                    ? "Every complaint. A clear next step."
                    : view === "Cases"
                      ? "Complaint queue"
                      : view === "Batch upload"
                        ? "Process complaints together"
                        : "Evidence behind the engine"}
              </h1>
              <p>
                {view === "Overview"
                  ? "Understand the workload, review the signals, and keep complaints moving."
                  : view === "Analyze"
                    ? "Transform a narrative into a categorized, explainable case for review."
                    : view === "Cases"
                      ? "Search your saved cases and inspect the reasoning behind each decision."
                      : view === "Batch upload"
                        ? "Bring in a CSV, review the narratives, and analyze them in one workflow."
                        : "Measured performance, transparent methods, and honest model readiness."}
              </p>
            </div>
            <div className="heading-actions">
              {view === "Overview" ? (
                <>
                  <button
                    className="button ghost"
                    aria-label="Refresh workspace"
                    onClick={() => void refresh()}
                    disabled={loading}
                  >
                    <RefreshCw size={16} className={loading ? "spin" : ""} />
                  </button>
                  <button
                    className="button primary"
                    onClick={() => navigate("Analyze")}
                  >
                    <Plus size={16} />
                    New analysis
                  </button>
                </>
              ) : view === "Cases" ? (
                <button
                  className="button secondary"
                  onClick={() => exportCases(items)}
                  disabled={!items.length}
                >
                  <ArrowDownToLine size={16} />
                  Export loaded
                </button>
              ) : null}
            </div>
          </div>
          {error ? (
            <div className="alert" role="alert">
              {error}
              <button onClick={() => void refresh()}>Try again</button>
            </div>
          ) : null}
          {loading && !items.length ? (
            <div className="loading-panel">
              <RefreshCw className="spin" size={24} />
              <p>Loading your workspace…</p>
            </div>
          ) : null}
          {view === "Overview" ? (
            <Overview
              analytics={analytics}
              items={items}
              inspect={setSelected}
              navigate={navigate}
            />
          ) : view === "Analyze" ? (
            <Analyze saved={() => void refresh()} health={health} />
          ) : view === "Cases" ? (
            <Cases items={items} inspect={setSelected} />
          ) : view === "Batch upload" ? (
            <Batch saved={() => void refresh()} />
          ) : (
            <Evidence health={health} />
          )}
          <footer className="page-footer">
            <span>
              <ShieldCheck size={14} /> Decision support · Human review remains
              essential
            </span>
            <span>
              Public CFPB narratives ·{" "}
              {health?.backend === "slm"
                ? "Fine-tuned SLM"
                : "Baseline demonstration"}
            </span>
          </footer>
        </main>
      </div>
      {selected ? <Drawer item={selected} onClose={closeDrawer} /> : null}
    </div>
  );
}
function Overview({
  analytics,
  items,
  inspect,
  navigate,
}: {
  analytics: Analytics;
  items: Complaint[];
  inspect: (item: Complaint) => void;
  navigate: (view: View) => void;
}) {
  const urgent =
    (analytics.by_priority.High ?? 0) + (analytics.by_priority.Critical ?? 0);
  return (
    <>
      <div className="kpi-grid">
        <div className="kpi featured">
          <span>
            TOTAL COMPLAINTS
            <Layers3 size={17} />
          </span>
          <strong>{analytics.total.toLocaleString()}</strong>
          <small>Saved and analyzed cases</small>
          <div className="kpi-decoration" />
        </div>
        <div className="kpi">
          <span>
            NEEDS REVIEW
            <ClipboardList size={17} />
          </span>
          <strong>{analytics.needs_review}</strong>
          <small>
            <span className="small-dot orange" />
            Flagged for human attention
          </small>
        </div>
        <div className="kpi">
          <span>
            HIGH / CRITICAL
            <ShieldCheck size={17} />
          </span>
          <strong>{urgent}</strong>
          <small>Rule-based urgency signals</small>
        </div>
        <div className="kpi">
          <span>
            AVG. PROCESSING
            <Activity size={17} />
          </span>
          <strong>
            {(analytics.average_latency_ms / 1000).toFixed(2)}
            <em>s</em>
          </strong>
          <small>Classification and explanation</small>
        </div>
      </div>
      <div className="overview-charts">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Complaints by product</h2>
              <p>Where the workload is concentrated</p>
            </div>
            <span className="tag">
              {Object.keys(analytics.by_product).length} products
            </span>
          </div>
          <Bars data={analytics.by_product} />
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Priority breakdown</h2>
              <p>Rules that guide the review queue</p>
            </div>
            <ShieldCheck size={19} className="muted" />
          </div>
          <div className="priority-list">
            {["Critical", "High", "Medium", "Low"].map((priority) => (
              <div key={priority}>
                <Priority value={priority} />
                <div className="priority-track">
                  <span
                    style={{
                      width: `${analytics.total ? ((analytics.by_priority[priority] ?? 0) / analytics.total) * 100 : 0}%`,
                    }}
                  />
                </div>
                <strong>{analytics.by_priority[priority] ?? 0}</strong>
              </div>
            ))}
          </div>
          <div className="panel-note">
            Priority reflects configured phrase rules, not a regulatory
            assessment.
          </div>
        </section>
      </div>
      <section className="panel activity-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent cases</h2>
            <p>The latest complaints in your workspace</p>
          </div>
          <button className="text-button" onClick={() => navigate("Cases")}>
            View all cases
            <ArrowUpRight size={16} />
          </button>
        </div>
        {items.length ? (
          <CaseTable items={items.slice(0, 5)} onInspect={inspect} />
        ) : (
          <Empty
            title="Your queue starts here"
            description="Analyze your first complaint to build a live view of operations."
          />
        )}
      </section>
      <div className="overview-bottom">
        <div>
          <CheckCircle2 size={20} />
          <span>
            <strong>A transparent workflow</strong>
            <small>
              Real predictions. Saved records. Inspectable explanations.
            </small>
          </span>
        </div>
        <button
          className="text-button"
          onClick={() => navigate("Model evidence")}
        >
          Explore model evidence
          <ArrowRight size={16} />
        </button>
      </div>
    </>
  );
}
function Analyze({
  saved,
  health,
}: {
  saved: () => void;
  health: Health | null;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Complaint | null>(null);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current) return;
    if (!text.trim()) {
      setError("Enter a complaint narrative before analyzing.");
      return;
    }
    inFlight.current = true;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await api.analyze(text));
      saved();
    } catch (e) {
      setError(message(e));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="analyze-layout">
      <section className="panel compose">
        <div className="panel-heading">
          <div>
            <h2>Complaint narrative</h2>
            <p>Start with the customer's own words</p>
          </div>
          <span className="tag">
            <span className="small-dot" />
            {health?.backend === "slm"
              ? "Fine-tuned Qwen2.5"
              : health?.backend === "baseline"
                ? "Baseline classifier"
                : "Connecting…"}
          </span>
        </div>
        <form onSubmit={(event) => void submit(event)}>
          <label className="sr-only" htmlFor="narrative">
            Complaint narrative
          </label>
          <textarea
            id="narrative"
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={6000}
            placeholder="Describe what happened, which financial product was involved, and what remains unresolved…"
          />
          <div className="input-meta">
            <span>Plain text · up to 6,000 characters</span>
            <span>{text.length.toLocaleString()} / 6,000</span>
          </div>
          {health?.backend === "slm" ? (
            <p className="model-input-note">
              Qwen2.5 predicts the product and issue using the first 2,000
              characters. Priority and routing use configured policies.
            </p>
          ) : null}
          {error ? (
            <div className="alert" role="alert">
              {error}
            </div>
          ) : null}
          <button
            className="button primary full"
            disabled={busy || !text.trim()}
          >
            {busy ? (
              <RefreshCw size={17} className="spin" />
            ) : (
              <Sparkles size={17} />
            )}{" "}
            {busy ? "Analyzing and saving…" : "Analyze complaint"}
            {busy ? null : <ArrowRight size={17} />}
          </button>
        </form>
        <div className="sample-inputs">
          <span className="overline">OR TRY AN EXAMPLE</span>
          {examples.map((example) => (
            <button
              key={example.label}
              onClick={() => setText(example.text)}
              disabled={busy}
            >
              {example.label}
              <ArrowUpRight size={14} />
            </button>
          ))}
        </div>
        <div className="privacy-note">
          <ShieldCheck size={17} />
          <p>
            Analysis and history stay in your local workspace. Avoid entering
            sensitive personal details.
          </p>
        </div>
      </section>
      <section
        className={`panel analysis-result ${result ? "has-result" : ""}`}
      >
        {result ? (
          <Result item={result} />
        ) : (
          <div className="result-placeholder">
            <div className="placeholder-orbit">
              <Sparkles size={29} />
            </div>
            <span className="overline">FROM NARRATIVE TO NEXT ACTION</span>
            <h2>Clarity starts with a complaint.</h2>
            <p>
              Your analysis will appear here with a product, issue, priority,
              and suggested route.
            </p>
            <div className="workflow-steps">
              <span>
                01 <strong>Classify</strong>
              </span>
              <ChevronRight size={13} />
              <span>
                02 <strong>Prioritize</strong>
              </span>
              <ChevronRight size={13} />
              <span>
                03 <strong>Route</strong>
              </span>
            </div>
            <small>
              Priority is rule based. Summaries are extractive previews.
            </small>
          </div>
        )}
      </section>
    </div>
  );
}
function Cases({
  items,
  inspect,
}: {
  items: Complaint[];
  inspect: (item: Complaint) => void;
}) {
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("All priorities");
  const [product, setProduct] = useState("All products");
  const filtered = useMemo(
    () =>
      items.filter(
        (item) =>
          (priority === "All priorities" || item.priority === priority) &&
          (product === "All products" || item.product === product) &&
          [item.id, item.text, item.product, item.issue, item.department]
            .join(" ")
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [items, query, priority, product],
  );
  return (
    <section className="panel cases-panel">
      <div className="filter-bar">
        <div className="search-input">
          <Search size={17} />
          <input
            aria-label="Search complaints"
            placeholder="Search case ID, narrative, or issue…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <select
          aria-label="Filter by priority"
          value={priority}
          onChange={(event) => setPriority(event.target.value)}
        >
          {["All priorities", "Critical", "High", "Medium", "Low"].map(
            (value) => (
              <option key={value}>{value}</option>
            ),
          )}
        </select>
        <select
          aria-label="Filter by product"
          value={product}
          onChange={(event) => setProduct(event.target.value)}
        >
          {["All products", ...new Set(items.map((item) => item.product))].map(
            (value) => (
              <option key={value}>{value}</option>
            ),
          )}
        </select>
      </div>
      <div className="table-summary">
        <span>
          <strong>{filtered.length}</strong> cases{" "}
          {filtered.length !== items.length
            ? `of ${items.length}`
            : "in the queue"}
        </span>
        <button
          className="text-button"
          onClick={() => exportCases(filtered)}
          disabled={!filtered.length}
        >
          <ArrowDownToLine size={14} />
          Export view
        </button>
      </div>
      {filtered.length ? (
        <CaseTable items={filtered} onInspect={inspect} />
      ) : (
        <Empty
          title={items.length ? "No matching cases" : "No cases yet"}
          description={
            items.length
              ? "Try another search or clear the filters."
              : "Run an analysis to add your first saved complaint."
          }
        />
      )}
      <div className="table-foot">
        <span>All records saved locally</span>
        <span>Click a case to inspect its complete analysis</span>
      </div>
    </section>
  );
}
function Batch({ saved }: { saved: () => void }) {
  const [texts, setTexts] = useState<string[]>([]);
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BatchResult | null>(null);
  const inFlight = useRef(false);
  const uploadSequence = useRef(0);
  function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const sequence = ++uploadSequence.current;
    setError("");
    setResult(null);
    setTexts([]);
    setFilename(file.name);
    if (file.size > 2_000_000) {
      setError("Choose a CSV smaller than 2 MB.");
      return;
    }
    Papa.parse<Record<string, string>>(file, {
      header: true,
      delimiter: ",",
      skipEmptyLines: true,
      complete: (parsed) => {
        if (sequence !== uploadSequence.current) return;
        if (!parsed.meta.fields?.includes("text")) {
          setError("The CSV needs a column named text.");
          return;
        }
        if (parsed.errors.length) {
          setError(
            "The CSV could not be parsed. Check quoting and column structure.",
          );
          return;
        }
        const narratives = parsed.data.map((row) => row.text?.trim() ?? "");
        if (!narratives.length) {
          setError("The CSV contains no complaint rows.");
          return;
        }
        if (narratives.length > 20) {
          setError(
            "Use a batch of up to 20 rows. Split larger files into smaller batches.",
          );
          return;
        }
        if (narratives.some((text) => !text || text.length > 6000)) {
          setError(
            "Every row must contain a non-empty text narrative of at most 6,000 characters.",
          );
          return;
        }
        setTexts(narratives);
      },
      error: (e) => {
        if (sequence === uploadSequence.current) setError(e.message);
      },
    });
  }
  async function run() {
    if (inFlight.current || result || !texts.length) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      setResult(await api.batch(texts));
      saved();
    } catch (e) {
      setError(message(e));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="batch-layout">
      <section className="panel batch-upload">
        <div className="panel-heading">
          <div>
            <h2>Upload a complaint file</h2>
            <p>One narrative per row, ready for analysis</p>
          </div>
          <FileUp size={20} className="muted" />
        </div>
        <label className="drop-zone">
          <span className="upload-icon">
            <FileUp size={26} />
          </span>
          <strong>{filename || "Choose your CSV file"}</strong>
          <span>
            {filename
              ? "Select another file to replace it"
              : "Click to browse a file from your computer"}
          </span>
          <small>CSV · 2 MB maximum · 20 rows per batch</small>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label="Upload complaint CSV"
            onChange={upload}
            disabled={busy}
          />
        </label>
        {error ? (
          <div className="alert" role="alert">
            {error}
          </div>
        ) : null}
        <div className="batch-spec">
          <strong>A simple format</strong>
          <p>
            Include a column named <code>text</code>. Other columns are ignored.
            Quoted commas and multiline narratives are supported.
          </p>
          <button
            className="text-button"
            onClick={() =>
              download(
                "complaintiq-template.csv",
                Papa.unparse([{ text: examples[0].text }]),
              )
            }
          >
            <ArrowDownToLine size={14} />
            Download CSV template
          </button>
        </div>
        <button
          className="button primary full"
          disabled={!texts.length || busy || !!result}
          onClick={() => void run()}
        >
          {busy ? (
            <RefreshCw className="spin" size={17} />
          ) : (
            <Sparkles size={17} />
          )}{" "}
          {busy
            ? "Processing complaints…"
            : `Analyze ${texts.length || ""} complaints`}
          <ArrowRight size={17} />
        </button>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{result ? "Batch results" : "Preview before processing"}</h2>
            <p>
              {result
                ? `${result.saved} complaints saved to your queue`
                : "Nothing is saved until you start analysis"}
            </p>
          </div>
          {texts.length ? (
            <span className="tag">{texts.length} rows</span>
          ) : null}
        </div>
        {result ? (
          <>
            <div className="batch-results">
              {result.items.map((item, index) => (
                <div key={"id" in item ? item.id : index}>
                  <span className="row-index">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div>
                    {"error" in item ? (
                      <>
                        <strong>Could not process</strong>
                        <p>{item.error}</p>
                      </>
                    ) : (
                      <>
                        <strong>{item.product}</strong>
                        <p>{item.issue}</p>
                      </>
                    )}
                  </div>
                  {"priority" in item ? (
                    <Priority value={item.priority} />
                  ) : null}
                </div>
              ))}
            </div>
            <button
              className="button secondary batch-export"
              onClick={() =>
                download(
                  "complaintiq-batch.csv",
                  Papa.unparse(
                    result.items.map((item) => ({
                      id: "id" in item ? item.id : "",
                      text: item.text,
                      product: "product" in item ? item.product : "",
                      issue: "issue" in item ? item.issue : "",
                      priority: "priority" in item ? item.priority : "",
                      department: "department" in item ? item.department : "",
                      error: "error" in item ? item.error : "",
                    })),
                    { escapeFormulae: true },
                  ),
                )
              }
            >
              <ArrowDownToLine size={15} />
              Export results
            </button>
          </>
        ) : texts.length ? (
          <div className="batch-preview">
            {texts.map((text, index) => (
              <div key={index}>
                <span className="row-index">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <p>{text}</p>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="Your file preview will appear here"
            description="Upload a CSV to validate its structure and inspect the narratives."
          />
        )}
      </section>
    </div>
  );
}
function Evidence({ health }: { health: Health | null }) {
  const [report, setReport] = useState<Evaluation | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api
      .evaluation()
      .then((data) => {
        if (active) setReport(data);
      })
      .catch((e) => {
        if (active) setError(message(e));
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <>
      <div className="evidence-banner">
        <div className="evidence-icon">
          <BarChart3 size={25} />
        </div>
        <div>
          <span className="overline">MEASURED, NOT ASSUMED</span>
          <h2>An engine you can inspect.</h2>
          <p>
            Held-out results show how well the measured model classifies
            complaints.
          </p>
        </div>
        <span className="tag">
          {report?.backend === "slm"
            ? "Fine-tuned SLM evaluation"
            : "Baseline evaluation"}
        </span>
      </div>
      {error ? (
        <div className="alert" role="alert">
          {error}
        </div>
      ) : null}
      {report ? (
        <>
          <div className="kpi-grid evidence-kpis">
            <div className="kpi">
              <span>PRODUCT ACCURACY</span>
              <strong>
                {(report.product.accuracy * 100).toFixed(1)}
                <em>%</em>
              </strong>
              <small>{report.test_size} held-out complaints</small>
            </div>
            <div className="kpi">
              <span>PRODUCT MACRO F1</span>
              <strong>{report.product.f1_macro.toFixed(3)}</strong>
              <small>Equal weight across product classes</small>
            </div>
            <div className="kpi">
              <span>ISSUE MACRO F1</span>
              <strong>{report.issue.f1_macro.toFixed(3)}</strong>
              <small>Performance across issue classes</small>
            </div>
            <div className="kpi">
              <span>JOINT ACCURACY</span>
              <strong>
                {(report.joint_accuracy * 100).toFixed(1)}
                <em>%</em>
              </strong>
              <small>Product and issue both correct</small>
            </div>
          </div>
          <div className="evidence-grid">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Product confusion matrix</h2>
                  <p>Actual labels in rows · predictions in columns</p>
                </div>
              </div>
              <div className="matrix-scroll">
                <table className="matrix">
                  <thead>
                    <tr>
                      <th>Actual / predicted</th>
                      {report.product.labels.map((label) => (
                        <th key={label}>{label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.product.confusion_matrix.map((row, i) => (
                      <tr key={i}>
                        <th>{report.product.labels[i] ?? "Unknown"}</th>
                        {row.map((count, j) => (
                          <td key={j} className={i === j ? "diagonal" : ""}>
                            {count}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="panel-note">
                Results apply to this demonstration sample and label taxonomy.
              </div>
            </section>
            <section className="panel active-model-card">
              <div className="panel-heading">
                <div>
                  <h2>Active classification model</h2>
                  <p>The engine analyzing new complaints</p>
                </div>
                <span className={`tag ${health ? "ready" : ""}`}>
                  <CheckCircle2 size={13} /> {health ? "In use" : "Unavailable"}
                </span>
              </div>
              <div className="active-model-hero">
                <div className="active-model-icon">
                  <Sparkles size={25} />
                </div>
                <div>
                  <span className="overline">
                    {health?.backend === "slm"
                      ? "FINE-TUNED SMALL LANGUAGE MODEL"
                      : "TRADITIONAL ML CLASSIFIER"}
                  </span>
                  <h3>
                    {health?.backend === "slm"
                      ? "Qwen2.5-1.5B-Instruct"
                      : health?.backend === "baseline"
                        ? "TF-IDF + Logistic Regression"
                        : "Connecting to engine…"}
                  </h3>
                  <p>
                    {health?.backend === "slm"
                      ? "Predicts financial product and complaint issue on your Mac."
                      : "Predicts financial product and complaint issue locally."}
                  </p>
                </div>
              </div>
              <dl className="model-facts">
                <div>
                  <dt>Execution</dt>
                  <dd>
                    Local · {health?.backend === "slm" ? "Apple M1" : "CPU"}
                  </dd>
                </div>
                {health?.backend === "slm" ? (
                  <>
                    <div>
                      <dt>Fine-tuning</dt>
                      <dd>
                        QLoRA ·{" "}
                        {(health.training_size ?? 9000).toLocaleString()}{" "}
                        complaints
                      </dd>
                    </div>
                    <div>
                      <dt>Model format</dt>
                      <dd>GGUF · Q4_K_M</dd>
                    </div>
                  </>
                ) : null}
                <div>
                  <dt>Model output</dt>
                  <dd>Product + issue</dd>
                </div>
              </dl>
              <div className="model-artifact">
                <span>Loaded model</span>
                <code>{health?.model_version ?? "Checking connection…"}</code>
              </div>
              <p className="active-model-note">
                New complaints use this engine. Saved cases retain the model
                that originally classified them.
              </p>
              <button
                className="text-button"
                onClick={() =>
                  download(
                    "evaluation.json",
                    JSON.stringify(report, null, 2),
                    "application/json",
                  )
                }
              >
                <ArrowDownToLine size={15} />
                Download evaluation report
              </button>
            </section>
          </div>
          <section className="panel methodology">
            <div className="panel-heading">
              <div>
                <h2>How each result is produced</h2>
                <p>
                  A clear source for classification, priority, and complaint
                  previews
                </p>
              </div>
            </div>
            <div className="method-grid">
              <div>
                <span>01</span>
                <h3>Classification</h3>
                <p>
                  {health?.backend === "slm"
                    ? "A fine-tuned Qwen2.5 model predicts product and issue locally. Outputs must match an allowed label pair. Inference uses the first 2,000 characters of each complaint."
                    : "TF-IDF and Logistic Regression predict product and issue from the narrative."}
                </p>
              </div>
              <div>
                <span>02</span>
                <h3>Priority & routing</h3>
                <p>
                  Configured phrase rules set urgency. Category mappings suggest
                  a team and action.
                </p>
              </div>
              <div>
                <span>03</span>
                <h3>Explanation</h3>
                <p>
                  {health?.backend === "slm"
                    ? "Priority reasons come from explicit rules. The complaint preview is extractive; SLM token attribution is disabled to keep local inference fast."
                    : "LIME attributes the product prediction. The complaint preview is extractive."}
                </p>
              </div>
            </div>
            <div className="panel-note">
              {Array.isArray(report.limitations)
                ? report.limitations.join(" ")
                : report.limitations}
            </div>
          </section>
        </>
      ) : !error ? (
        <div className="loading-panel">
          <RefreshCw className="spin" size={22} />
          Loading measured evidence…
        </div>
      ) : null}
    </>
  );
}
