function Card({ label, value, accent, mono = true }) {
  return (
    <div className="stat-card" style={{ "--card-accent": accent }}>
      <div className="stat-label">{label}</div>
      <div className={mono ? "stat-value stat-value-mono" : "stat-value"}>{value}</div>
    </div>
  );
}

export default function StatsCards({ metrics }) {
  if (!metrics) return null;

  const {
    total_payments = 0,
    recovered_count = 0,
    unrecoverable_count = 0,
    recovery_rate = 0,
  } = metrics;

  return (
    <section className="stats-grid">
      <Card label="Total Payments" value={total_payments} accent="var(--c-neutral)" />
      <Card label="Recovered" value={recovered_count} accent="var(--c-recovered)" />
      <Card label="Unrecoverable" value={unrecoverable_count} accent="var(--c-unrecoverable)" />
      <Card
        label="Recovery Rate"
        value={`${(recovery_rate * 100).toFixed(1)}%`}
        accent="var(--c-primary)"
      />
    </section>
  );
}
