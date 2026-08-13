import React, { useEffect, useState } from "react";

// Provided starting point: lists loans from the backend (works out of the box
// once the API is running). The repayment UI is YOUR task — see the TODOs.

const fmt = (n) => "₦" + Number(n).toLocaleString();

export default function App() {
  const [loans, setLoans] = useState([]);
  const [error, setError] = useState(null);

  const load = () =>
    fetch("/loans")
      .then((r) => r.json())
      .then(setLoans)
      .catch((e) => setError(String(e)));

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Loan servicing</h1>
      {error && <p style={{ color: "crimson" }}>Failed to load loans: {error}</p>}

      <table style={{ borderCollapse: "collapse", width: "100%" }} border="1" cellPadding="8">
        <thead>
          <tr>
            <th>ID</th>
            <th>Borrower</th>
            <th style={{ textAlign: "right" }}>Outstanding</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {loans.map((l) => (
            <tr key={l.id}>
              <td>{l.id}</td>
              <td>{l.borrower_name}</td>
              <td style={{ textAlign: "right" }}>{fmt(l.outstanding)}</td>
              <td>{l.status}</td>
              <td>
                {/* TODO(candidate): a "Repay" action that POSTs to
                    /loans/{l.id}/repayments and refreshes the row on success. */}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/*
        TODO(candidate): build a small repayment form.
        - Pick a loan, enter an amount, submit to POST /loans/{id}/repayments.
        - Send the role header (e.g. X-Role: system) so the request is authorised.
        - Show the result and the updated balance; call load() to refresh.
        - Handle the error cases the API returns (403 / 409 / 422) with a message.
        Keep it small and readable — we're looking at how you wire state, calls,
        and error handling, not at visual polish.
      */}
    </div>
  );
}
