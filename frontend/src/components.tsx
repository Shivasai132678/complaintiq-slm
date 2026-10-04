import { ArrowUpRight, Check, Clock3, Copy, FileText, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Complaint } from "./types";
export function Priority({ value }: { value: string }) {
  return (
    <span className={`badge priority-${value.toLowerCase()}`}>
      <i />
      {value}
    </span>
  );
}
export function Empty({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty">
      <FileText size={28} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
export function Bars({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return entries.length ? (
    <div className="bars">
      {entries.map(([label, count], i) => (
        <div className="bar-row" key={label}>
          <div>
            <span>{label}</span>
            <strong>
              {count}
              <small>{Math.round((count / total) * 100)}%</small>
            </strong>
          </div>
          <div className="bar-track">
            <span
              style={{
                width: `${(count / total) * 100}%`,
                background: ["#287f75", "#72aba0", "#a9c8be", "#c5d6ce"][i % 4],
              }}
            />
          </div>
        </div>
      ))}
    </div>
  ) : (
    <Empty
      title="No distribution yet"
      description="Analyze complaints to see the workload here."
    />
  );
}
export function dateLabel(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}
export function CaseTable({
  items,
  onInspect,
}: {
  items: Complaint[];
  onInspect: (item: Complaint) => void;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Case / narrative</th>
            <th>Product</th>
            <th>Priority</th>
            <th>Route</th>
            <th>Received</th>
            <th>
              <span className="sr-only">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} onClick={() => onInspect(item)}>
              <td>
                <button className="case-link" onClick={() => onInspect(item)}>
                  {item.id}
                </button>
                <span className="narrative-preview">{item.text}</span>
              </td>
              <td>{item.product}</td>
              <td>
                <Priority value={item.priority} />
              </td>
              <td>{item.department.replace(" Team", "")}</td>
              <td className="nowrap">{dateLabel(item.created_at)}</td>
              <td>
                <button
                  className="icon-button"
                  aria-label={`Inspect ${item.id}`}
                  onClick={() => onInspect(item)}
                >
                  <ArrowUpRight size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Result({ item }: { item: Complaint }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(item, null, 2));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }
  return (
    <div className="result-body">
      <div className="result-top">
        <span className="overline">PRODUCT & ISSUE · MODEL PREDICTION</span>
        <span className="status-dot">Saved to queue</span>
      </div>
      <div className="prediction-source">
        <span className="tag ready">
          {item.backend === "slm" ? "Fine-tuned SLM" : "Baseline classifier"}
        </span>
        <span>
          {item.backend === "slm"
            ? "Qwen2.5-1.5B · runs locally"
            : "TF-IDF + Logistic Regression"}
        </span>
      </div>
      <div className="result-title">
        <h2>{item.product}</h2>
      </div>
      <p className="result-issue">{item.issue}</p>
      {item.input_truncated ? (
        <p className="excerpt-notice">
          Classification used the first{" "}
          {item.input_chars_used?.toLocaleString() ?? "2,000"} characters. The
          full narrative is saved with this case.
        </p>
      ) : null}
      <div className="workflow-divider">
        <div className="workflow-heading">
          <span className="overline">WORKFLOW ASSESSMENT</span>
          <Priority value={item.priority} />
        </div>
        <p>
          Priority and routing follow configured policies after classification.
        </p>
      </div>
      <div className="detail-grid">
        <div>
          <span>ROUTED TO</span>
          <strong>{item.department}</strong>
        </div>
        <div>
          <span>REVIEW STATUS</span>
          <strong>{item.status}</strong>
        </div>
      </div>
      <section className="result-section">
        <h4>
          Priority assessment <span>POLICY CHECK</span>
        </h4>
        <p>{item.priority_reason}</p>
      </section>
      <section className="result-section next-step">
        <h4>
          Suggested next step <span>ROUTING POLICY</span>
        </h4>
        <p>{item.action}</p>
      </section>
      <section className="result-section">
        <h4>
          Complaint preview <span>NARRATIVE EXCERPT</span>
        </h4>
        <p>{item.summary}</p>
      </section>
      {item.explanation?.length > 0 ? (
        <section className="result-section">
          <h4>
            What influenced the classification <span>LIME</span>
          </h4>
          <div className="tokens">
            {item.explanation.map((value) => (
              <span
                key={value.token}
                className={value.weight < 0 ? "negative" : ""}
              >
                {value.token}
                <small>
                  {value.weight > 0 ? "+" : ""}
                  {value.weight.toFixed(3)}
                </small>
              </span>
            ))}
          </div>
          <p className="muted tiny">
            Token weights explain the product prediction; they are not
            confidence scores.
          </p>
        </section>
      ) : null}
      <div className="result-footer">
        <span>
          <Clock3 size={13} />
          {(item.latency_ms / 1000).toFixed(2)}s ·{" "}
          {item.cached
            ? "Cached result"
            : item.backend === "baseline"
              ? "Baseline classifier"
              : "Local SLM inference"}
        </span>
        <button className="text-button" onClick={() => void copy()}>
          {copied ? <Check size={14} /> : <Copy size={14} />}{" "}
          {copied ? "Copied" : "Copy record"}
        </button>
      </div>
    </div>
  );
}
export function Drawer({
  item,
  onClose,
}: {
  item: Complaint;
  onClose: () => void;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    ref.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const dialog = ref.current?.closest('[role="dialog"]');
        const elements = dialog?.querySelectorAll<HTMLElement>(
          'button:not([disabled]),a[href],input,select,textarea,[tabindex="0"]',
        );
        if (!elements?.length) return;
        const first = elements[0],
          last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("keydown", escape);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [onClose]);
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <section
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`Case ${item.id}`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer-header">
          <div>
            <span className="overline">CASE DETAIL</span>
            <h3>{item.id}</h3>
          </div>
          <button
            ref={ref}
            className="icon-button"
            aria-label="Close case details"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        <Result item={item} />
        <section className="full-narrative">
          <h4>Original narrative</h4>
          <p>{item.text}</p>
          <span className="muted tiny">
            {new Date(item.created_at).toLocaleString()} · {item.model_version}
          </span>
        </section>
      </section>
    </div>
  );
}
