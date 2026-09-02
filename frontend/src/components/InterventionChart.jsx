import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const INTERVENTION_COLORS = {
  retry_now: "#34D399",
  retry_later: "#FBBF24",
  suggest_alt_method: "#60A5FA",
  hold: "#8B93A7",
  unrecoverable: "#F87171",
};

const FALLBACK = "#8B93A7";

function labelFor(key) {
  return key
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export default function InterventionChart({ breakdown }) {
  const entries = Object.entries(breakdown || {});
  const data = entries.map(([key, value]) => ({ name: labelFor(key), key, value }));

  return (
    <div className="chart-panel">
      <h2 className="chart-title">Intervention Breakdown</h2>
      {data.length === 0 ? (
        <div className="chart-empty">No interventions recorded yet.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--panel-border)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-body)" }}
              axisLine={{ stroke: "var(--panel-border)" }}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "var(--panel-border)", opacity: 0.4 }}
              contentStyle={{
                background: "var(--panel-raised)",
                border: "1px solid var(--panel-border)",
                borderRadius: 8,
                fontFamily: "var(--font-mono)",
                fontSize: 12,
              }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.key} fill={INTERVENTION_COLORS[entry.key] || FALLBACK} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
