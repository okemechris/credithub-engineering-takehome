import React, { useCallback, useEffect, useState } from "react";
import "./styles.css";

// Provided starting point. The loans table, the payments feed, and the
// "Simulate incoming payment" button all work. Reconciling a payment — the
// Apply action — is YOUR task (backend + the apply() wiring below).

const ngn = new Intl.NumberFormat("en-NG", {
  style: "currency",
  currency: "NGN",
  maximumFractionDigits: 2,
});

const LOAN_LABEL = { active: "Active", paid_off: "Paid off", cancelled: "Cancelled", written_off: "Written off" };
const PAY_LABEL = { pending: "Pending", applied: "Applied", rejected: "Rejected" };

export default function App() {
  const [loans, setLoans] = useState(null);
  const [events, setEvents] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    Promise.all([
      fetch("/loans").then((r) => { if (!r.ok) throw new Error(`loans HTTP ${r.status}`); return r.json(); }),
      fetch("/payment-events").then((r) => { if (!r.ok) throw new Error(`events HTTP ${r.status}`); return r.json(); }),
    ])
      .then(([l, e]) => { setLoans(l); setEvents(e); })
      .catch((err) => setError(String(err.message || err)));
  }, []);

  useEffect(load, [load]);

  const simulate = async () => {
    setBusy(true);
    try {
      await fetch("/simulate/payment", { method: "POST" });
      load();
    } finally {
      setBusy(false);
    }
  };

  const apply = async (eventId) => {
    // TODO(candidate): reconcile this payment.
    //   POST /payment-events/{eventId}/apply   (send an X-Role header, e.g. "system")
    //   then call load() so the loan balance + event status update here.
    //   Surface the non-2xx cases (403 / 404) with a readable message.
    alert(`TODO: apply payment event #${eventId} → POST /payment-events/${eventId}/apply`);
  };

  const loanList = loans ?? [];
  const eventList = events ?? [];
  const active = loanList.filter((l) => l.status === "active");
  const outstanding = active.reduce((s, l) => s + (l.outstanding || 0), 0);
  const pending = eventList.filter((e) => e.status === "pending").length;

  return (
    <div className="app">
      <div className="brand">
        <h1>CreditHub</h1>
        <span className="tag">· Loan Servicing</span>
      </div>
      <p className="sub">Payments land from the rails; reconcile them against loans.</p>

      {error && (
        <div className="banner">
          Couldn’t reach the API on <b>:8137</b> — is it running? ({error})
        </div>
      )}

      <div className="stats">
        <div className="stat"><div className="k">Active loans</div><div className="v">{loans ? active.length : "—"}</div></div>
        <div className="stat"><div className="k">Outstanding · active</div><div className="v">{loans ? ngn.format(outstanding) : "—"}</div></div>
        <div className="stat"><div className="k">Pending payments</div><div className="v">{events ? pending : "—"}</div></div>
      </div>

      {/* Payments feed */}
      <div className="card">
        <div className="card-h">
          <span>Payments feed</span>
          <button className="btn btn-primary" onClick={simulate} disabled={busy}>
            {busy ? "Simulating…" : "Simulate incoming payment"}
          </button>
        </div>
        <table className="feed">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Loan</th>
              <th className="num">Amount</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {events === null && !error &&
              [0, 1, 2].map((i) => (
                <tr key={i}><td colSpan="5"><div className="skeleton" /></td></tr>
              ))}

            {events &&
              eventList.map((e) => (
                <tr key={e.id}>
                  <td className="ref">
                    {e.external_ref}
                    <div className="chan">{e.channel}</div>
                  </td>
                  <td>Loan #{e.loan_id}</td>
                  <td className="num">{ngn.format(e.amount)}</td>
                  <td>
                    <span className={`pbadge ${e.status}`}>{PAY_LABEL[e.status] || e.status}</span>
                    {e.reason ? <div className="chan">{e.reason}</div> : null}
                  </td>
                  <td className="num">
                    {e.status === "pending" ? (
                      <button className="btn" onClick={() => apply(e.id)}>Apply →</button>
                    ) : null}
                  </td>
                </tr>
              ))}

            {events && eventList.length === 0 && (
              <tr><td colSpan="5" className="muted">No payments yet — hit “Simulate incoming payment”.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Loans */}
      <div className="section-title">Loans</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Borrower</th>
              <th className="num">Principal</th>
              <th className="num">Outstanding</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loans === null && !error &&
              [0, 1, 2].map((i) => (
                <tr key={i}><td colSpan="4"><div className="skeleton" /></td></tr>
              ))}

            {loans &&
              loanList.map((l) => (
                <tr key={l.id}>
                  <td>
                    <div className="name">{l.borrower_name}</div>
                    <div className="sub-id">Loan #{l.id}</div>
                  </td>
                  <td className="num">{ngn.format(l.principal)}</td>
                  <td className="num">{ngn.format(l.outstanding)}</td>
                  <td><span className={`badge ${l.status}`}>{LOAN_LABEL[l.status] || l.status}</span></td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="todo">
        <h3>Reconciliation — your task</h3>
        Wire the <b>Apply</b> action: reconcile a pending payment against its loan.
        Build <code>POST /payment-events/&#123;id&#125;/apply</code> on the backend
        (idempotent, money-correct, audited — see <code>README.md</code>), then wire{" "}
        <code>apply()</code> in <code>src/App.jsx</code> so the loan balance and the
        event status update here. Handle a rail redelivery (duplicate reference), a
        payment for a closed loan, and the <code>403 / 404</code> cases cleanly — to
        the same bar as the rest of this screen.
      </div>
    </div>
  );
}
