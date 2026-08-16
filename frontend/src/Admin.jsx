import React, { useEffect, useState } from "react";
import { ngn } from "./format";

// Reconciliation happens on receipt (see app/payments.py) — every event here
// already landed as "applied" or "rejected". This view exists for an operator
// to see, at a glance, whether reconciliation is healthy and which payments
// need a human to look at them.

// Keys here match app.models.RejectionReason's values exactly, so an event's
// own `reason_code` (set by the backend at reject time — see
// app/payments.py's _rejection_reason) can be used directly as a lookup key,
// rather than re-deriving a category by pattern-matching `reason`'s free
// text, which the backend is free to reword without warning.
const ISSUE_TYPES = ["duplicate", "unknown_loan", "closed_loan", "overpayment", "other"];

const ISSUE_LABEL = {
  duplicate: "Duplicate redelivery",
  unknown_loan: "Unknown loan",
  closed_loan: "Loan not active",
  overpayment: "Overpayment",
  other: "Other",
};

const issueOf = (e) => e.reason_code ?? "other";

const dt = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

export default function Admin({ events }) {
  const [auditLog, setAuditLog] = useState(null);
  const [auditError, setAuditError] = useState(null);
  const [filter, setFilter] = useState("all");

  const applied = events.filter((e) => e.status === "applied");
  const rejected = events.filter((e) => e.status === "rejected");
  const reconciled = applied.length + rejected.length;
  const failureRate = reconciled ? (rejected.length / reconciled) * 100 : 0;

  // The audit trail only grows on *applied* payments (see app/payments.py's
  // _apply -> record_audit) — a rejection never writes an audit row — so
  // this only needs to refetch when that count changes, not on every event
  // (a rejected Simulate/Resend, the common case in this demo, would
  // otherwise trigger a full unpaginated re-GET of the whole log for no
  // change). `ignore` guards against an in-flight fetch resolving after a
  // newer one and overwriting fresher state with stale data.
  useEffect(() => {
    let ignore = false;
    fetch("/audit-log")
      .then((r) => { if (!r.ok) throw new Error(`audit-log HTTP ${r.status}`); return r.json(); })
      .then((data) => { if (!ignore) setAuditLog(data); })
      .catch((err) => { if (!ignore) setAuditError(String(err.message || err)); });
    return () => { ignore = true; };
  }, [applied.length]);

  const counts = Object.fromEntries(ISSUE_TYPES.map((t) => [t, 0]));
  for (const e of rejected) counts[issueOf(e)]++;

  const visible = filter === "all" ? rejected : rejected.filter((e) => issueOf(e) === filter);

  return (
    <>
      <div className="stats">
        <div className="stat"><div className="k">Applied</div><div className="v">{applied.length}</div></div>
        <div className="stat"><div className="k">Rejected</div><div className="v">{rejected.length}</div></div>
        <div className="stat"><div className="k">Total reconciled</div><div className="v">{reconciled}</div></div>
        <div className="stat"><div className="k">Failure rate</div><div className="v">{failureRate.toFixed(1)}%</div></div>
      </div>

      <div className="section-title">Issues needing attention</div>
      <div className="card">
        <div className="chips">
          <button className={`chip ${filter === "all" ? "active" : ""}`} onClick={() => setFilter("all")}>
            All <span className="chip-n">{rejected.length}</span>
          </button>
          {ISSUE_TYPES.map((t) => (
            <button
              key={t}
              className={`chip ibadge-${t} ${filter === t ? "active" : ""}`}
              onClick={() => setFilter(t)}
              disabled={counts[t] === 0}
            >
              {ISSUE_LABEL[t]} <span className="chip-n">{counts[t]}</span>
            </button>
          ))}
        </div>

        {rejected.length === 0 ? (
          <div className="empty">No rejected payments — reconciliation is clean.</div>
        ) : (
          <table className="feed">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Loan</th>
                <th className="num">Amount</th>
                <th>Issue</th>
                <th>Received</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((e) => (
                <tr key={e.id}>
                  <td className="ref">{e.external_ref}<div className="chan">{e.channel}</div></td>
                  <td>Loan #{e.loan_id}</td>
                  <td className="num">{ngn.format(e.amount)}</td>
                  <td>
                    <span className={`ibadge ibadge-${issueOf(e)}`}>{ISSUE_LABEL[issueOf(e)]}</span>
                    <div className="chan">{e.reason}</div>
                  </td>
                  <td className="muted">{dt(e.received_at)}</td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr><td colSpan="5" className="muted">No issues in this category.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <div className="section-title">Activity trail</div>
      <div className="card">
        {auditError && <div className="empty">Couldn’t load the audit log ({auditError}).</div>}
        {!auditError && auditLog && auditLog.length === 0 && (
          <div className="empty">No audit entries yet.</div>
        )}
        {!auditError && auditLog && auditLog.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {auditLog.slice(0, 25).map((a) => (
                <tr key={a.id}>
                  <td className="muted">{dt(a.created_at)}</td>
                  <td>{a.action}</td>
                  <td>{a.entity} #{a.entity_id}</td>
                  <td className="muted">{a.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
