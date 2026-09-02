import { computeStageTimeline, stageMeta } from "../utils/audit";

function formatClock(ms) {
  const d = new Date(ms);
  return d.toISOString().slice(11, 23); // HH:MM:SS.mmm
}

export default function ExecutionTimeline({ records }) {
  const { entries, rangeStart, rangeEnd } = computeStageTimeline(records);
  const totalMs = rangeEnd - rangeStart;

  return (
    <section className="chart-panel timeline-panel">
      <div className="audit-header">
        <h2 className="chart-title">Batch Execution Timeline</h2>
        {entries.length > 0 && (
          <span className="audit-count mono">
            {totalMs < 1000 ? `${totalMs}ms` : `${(totalMs / 1000).toFixed(2)}s`} total
          </span>
        )}
      </div>

      {entries.length === 0 ? (
        <div className="chart-empty">No execution data yet.</div>
      ) : (
        <div className="timeline-track-wrap">
          {entries.map((e) => {
            const meta = stageMeta(e.stage);
            const left = ((e.start - rangeStart) / totalMs) * 100;
            const width = Math.max(((e.end - e.start) / totalMs) * 100, 1.5);
            return (
              <div className="timeline-row" key={e.stage}>
                <div className="timeline-row-label">
                  <span className="timeline-dot" style={{ background: meta.color }} />
                  {meta.agent}
                  <span className="mono muted timeline-count"> · {e.count}</span>
                </div>
                <div className="timeline-track">
                  <div
                    className="timeline-bar"
                    style={{ left: `${left}%`, width: `${width}%`, background: meta.color }}
                    title={`${meta.agent}: ${formatClock(e.start)} – ${formatClock(e.end)}`}
                  />
                </div>
              </div>
            );
          })}
          <div className="timeline-axis">
            <span className="mono">{formatClock(rangeStart)}</span>
            <span className="mono">{formatClock(rangeEnd)}</span>
          </div>
        </div>
      )}
    </section>
  );
}
