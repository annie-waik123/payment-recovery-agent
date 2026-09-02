import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

const ROOT_CAUSE_COLORS = {
  insufficient_funds: "#FBBF24",
  issuer_decline: "#F87171",
  network_timeout: "#60A5FA",
  expired_card: "#C084FC",
  risk_block: "#F97316",
  unknown: "#8B93A7",
};

const FALLBACK_PALETTE = ["#34D399", "#FBBF24", "#F87171", "#60A5FA", "#C084FC", "#8B93A7"];

function labelFor(key) {
  return key
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export default function RootCauseChart({ breakdown }) {
  const entries = Object.entries(breakdown || {});
  const data = entries.map(([key, value]) => ({ name: labelFor(key), key, value }));

  return (
    <div className="chart-panel">
      <h2 className="chart-title">Root Cause Breakdown</h2>
      {data.length === 0 ? (
        <div className="chart-empty">No classification data yet.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={95}
              paddingAngle={2}
              stroke="var(--panel)"
              strokeWidth={2}
            >
              {data.map((entry, i) => (
                <Cell
                  key={entry.key}
                  fill={ROOT_CAUSE_COLORS[entry.key] || FALLBACK_PALETTE[i % FALLBACK_PALETTE.length]}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "var(--panel-raised)",
                border: "1px solid var(--panel-border)",
                borderRadius: 8,
                fontFamily: "var(--font-mono)",
                fontSize: 12,
              }}
            />
            <Legend
              wrapperStyle={{ fontFamily: "var(--font-body)", fontSize: 12, color: "var(--text-muted)" }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
