import React, { useEffect, useState } from "react";
import "./styles.css";

// Provided starting point: a polished loan-servicing console. The loan list +
// summary work out of the box (proxied to the API). Building the repayment
// experience — to this bar — is YOUR task. See the note at the bottom.

const ngn = new Intl.NumberFormat("en-NG", {
  style: "currency",
  currency: "NGN",
  maximumFractionDigits: 2,
});

const STATUS_LABEL = {
  active: "Active",
  paid_off: "Paid off",
  cancelled: "Cancelled",
  written_off: "Written off",
};

export default function App() {
  const [loans, setLoans] = useState(null); // null = still loading
  const [error, setError] = useState(null);

  const load = () => {
    setError(null);
    fetch("/loans")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setLoans)
      .catch((e) => setError(String(e.message || e)));
  };

  useEffect(load, []);

  const list = loans ?? [];
  const active = list.filter((l) => l.status === "active");
  const outstanding = active.reduce((sum, l) => sum + (l.outstanding || 0), 0);

  return (
    <div className="app">
      <div className="brand">
        <h1>CreditHub</h1>
        <span className="tag">· Loan Servicing</span>
      </div>
      <p className="sub">Review outstanding loans and record repayments.</p>

      {error && (
        <div className="banner">
          Couldn’t load loans — is the API running on <b>:8137</b>? ({error})
        </div>
      )}

      <div className="stats">
        <div className="stat">
          <div className="k">Loans</div>
          <div className="v">{loans ? list.length : "—"}</div>
        </div>
        <div className="stat">
          <div className="k">Active</div>
          <div className="v">{loans ? active.length : "—"}</div>
        </div>
        <div className="stat">
          <div className="k">Outstanding · active</div>
          <div className="v">{loans ? ngn.format(outstanding) : "—"}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-h">
          <span>Loans</span>
          <span className="muted">{loans ? `${list.length} total` : ""}</span>
        </div>
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
              [0, 1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan="4">
                    <div className="skeleton" />
                  </td>
                </tr>
              ))}

            {loans &&
              list.map((l) => (
                <tr key={l.id}>
                  <td>
                    <div className="name">{l.borrower_name}</div>
                    <div className="sub-id">Loan #{l.id}</div>
                  </td>
                  <td className="num">{ngn.format(l.principal)}</td>
                  <td className="num">{ngn.format(l.outstanding)}</td>
                  <td>
                    <span className={`badge ${l.status}`}>
                      {STATUS_LABEL[l.status] || l.status}
                    </span>
                  </td>
                </tr>
              ))}

            {loans && list.length === 0 && (
              <tr>
                <td colSpan="4" className="muted">
                  No loans yet — run <code>python -m app.seed</code>.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="todo">
        <h3>Repayment — your task</h3>
        Build a small, well-crafted repayment experience that matches the bar
        above: pick a loan, enter an amount, submit to{" "}
        <code>POST /loans/&#123;id&#125;/repayments</code> (send an{" "}
        <code>X-Role</code> header), show the updated balance, and surface the
        API’s <code>403 / 409 / 422</code> responses cleanly. Wire it in{" "}
        <code>src/App.jsx</code>. We care about the state/call/error handling and
        that it looks as considered as the rest of this screen.
      </div>
    </div>
  );
}
