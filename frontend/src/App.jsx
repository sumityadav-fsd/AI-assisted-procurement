import { useEffect, useState } from "react";
import { getHealth, mocks, USE_MOCKS } from "./api.js";

const STEPS = [
  "1. Requirement intake",
  "2. ERP item matching",
  "3. RFQ generator",
  "4. Quotation intelligence",
  "5. Comparative statement",
  "6. Management decision",
];

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getHealth().then(setHealth).catch((e) => setError(e.message));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Vinayak ProcureAI</h1>
      <p>AI-assisted procurement decision support. A human makes the final decision.</p>

      <h2>Backend status</h2>
      {error && <p style={{ color: "crimson" }}>Backend unreachable: {error}</p>}
      {health && <pre>{JSON.stringify(health, null, 2)}</pre>}
      {!health && !error && <p>Checking…</p>}

      <h2>Workflow (not built yet)</h2>
      <ol>{STEPS.map((s) => <li key={s}>{s}</li>)}</ol>

      <p>
        Mock fixtures: {Object.keys(mocks).length} loaded ({mocks.comparison.vendors.length} vendors in the
        sample comparison). Mock mode: {USE_MOCKS ? "on" : "off"}.
      </p>
    </main>
  );
}
