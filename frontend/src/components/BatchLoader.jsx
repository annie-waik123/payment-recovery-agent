import { useState } from "react";
import { Play } from "lucide-react";

export default function BatchLoader({ onLoad, loading, error }) {
  const [batchId, setBatchId] = useState("");
  const [count, setCount] = useState(50);

  function handleLoadExisting(e) {
    e.preventDefault();
    if (batchId.trim()) onLoad({ mode: "load", batchId: batchId.trim() });
  }

  function handleSeedAndRun(e) {
    e.preventDefault();
    onLoad({ mode: "seed", count: Number(count) || 50 });
  }

  return (
    <section className="loader-panel">
      <form className="loader-row" onSubmit={handleLoadExisting}>
        <label className="loader-label" htmlFor="batch-id-input">
          Load batch
        </label>
        <input
          id="batch-id-input"
          className="loader-input"
          type="text"
          placeholder="batch_id (e.g. 0de529b000b5)"
          value={batchId}
          onChange={(e) => setBatchId(e.target.value)}
          spellCheck={false}
        />
        <button className="btn btn-secondary" type="submit" disabled={loading}>
          Load Dashboard
        </button>
      </form>

      <div className="loader-divider" aria-hidden="true" />

      <form className="loader-row" onSubmit={handleSeedAndRun}>
        <label className="loader-label" htmlFor="batch-count-input">
          Simulate Incident
        </label>
        <input
          id="batch-count-input"
          className="loader-input loader-input-narrow"
          type="number"
          min={1}
          max={500}
          value={count}
          onChange={(e) => setCount(e.target.value)}
        />
        <button className="btn btn-primary btn-demo-run" type="submit" disabled={loading}>
          <Play size={13} fill="currentColor" />
          <span>{loading ? "Processing Pipeline…" : "🚀 Run Live Incident Demo"}</span>
        </button>
      </form>

      {error && <div className="loader-error" role="alert">{error}</div>}
    </section>
  );
}
