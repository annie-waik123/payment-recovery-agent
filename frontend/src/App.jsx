import { useState, useCallback, useMemo } from "react";
import Header from "./components/Header";
import BatchLoader from "./components/BatchLoader";
import StatsCards from "./components/StatsCards";
import RevenueKPICards from "./components/RevenueKPICards";
import AIDiagnosticsPanel from "./components/AIDiagnosticsPanel";
import PipelineFlow from "./components/PipelineFlow";
import GuardrailDashboard from "./components/GuardrailDashboard";
import AgentPerformanceCards from "./components/AgentPerformanceCards";
import BatchSummary from "./components/BatchSummary";
import RootCauseChart from "./components/RootCauseChart";
import InterventionChart from "./components/InterventionChart";
import ExecutionTimeline from "./components/ExecutionTimeline";
import AuditTrailTable from "./components/AuditTrailTable";
import PaymentDetailDrawer from "./components/PaymentDetailDrawer";
import { createBatch, runBatch, getMetrics, getAudit, getPayments } from "./api/client";
import { computeStageCounts, computeAvgRetrySuccess, computeExecutorStats, groupAuditByPayment } from "./utils/audit";

export default function App() {
  const [batchId, setBatchId] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [audit, setAudit] = useState([]);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPaymentId, setSelectedPaymentId] = useState(null);

  const loadBatchData = useCallback(async (id) => {
    const [metricsData, auditData, paymentsData] = await Promise.all([
      getMetrics(id),
      getAudit(id),
      getPayments(id).catch(() => []),
    ]);
    setMetrics(metricsData);
    setAudit(auditData);
    setPayments(paymentsData || []);
    setBatchId(id);
  }, []);

  const handleLoad = useCallback(
    async ({ mode, batchId: existingId, count }) => {
      setLoading(true);
      setError(null);
      try {
        if (mode === "load") {
          await loadBatchData(existingId);
        } else {
          const created = await createBatch(count);
          const id = created.batch_id;
          await runBatch(id);
          await loadBatchData(id);
        }
      } catch (err) {
        const detail = err?.response?.data?.detail;
        setError(detail || err.message || "Something went wrong talking to the backend.");
      } finally {
        setLoading(false);
      }
    },
    [loadBatchData]
  );

  // Derived, client-side only — no extra API calls for any of these.
  const stageCounts = useMemo(() => computeStageCounts(audit), [audit]);
  const avgRetrySuccess = useMemo(() => computeAvgRetrySuccess(audit), [audit]);
  const executorStats = useMemo(() => computeExecutorStats(audit), [audit]);
  const groupedByPayment = useMemo(() => groupAuditByPayment(audit), [audit]);

  return (
    <div className="app-shell">
      <Header />

      <main className="app-main">
        <BatchLoader onLoad={handleLoad} loading={loading} error={error} />

        {batchId && (
          <>
            <div className="batch-tag">
              BATCH <span className="mono">{batchId}</span>
            </div>

            <StatsCards metrics={metrics} />
            <BatchSummary metrics={metrics} audit={audit} payments={payments} />
            <RevenueKPICards metrics={metrics} avgRetrySuccess={avgRetrySuccess} />
            <AIDiagnosticsPanel
              records={audit}
              metrics={metrics}
              payments={payments}
              onSelectPayment={setSelectedPaymentId}
            />
            <PipelineFlow stageCounts={stageCounts} metrics={metrics} executorStats={executorStats} />
            <AgentPerformanceCards metrics={metrics} audit={audit} />
            <GuardrailDashboard records={audit} />

            <section className="charts-row">
              <RootCauseChart breakdown={metrics?.root_cause_breakdown} />
              <InterventionChart breakdown={metrics?.intervention_breakdown} />
            </section>

            <ExecutionTimeline records={audit} />

            <AuditTrailTable records={audit} onSelectPayment={setSelectedPaymentId} />
          </>
        )}

        {!batchId && !loading && (
          <div className="empty-state">
            Seed a new batch, or load one by ID, to see the recovery pipeline in action.
          </div>
        )}
      </main>

      <PaymentDetailDrawer
        paymentId={selectedPaymentId}
        entries={selectedPaymentId ? groupedByPayment[selectedPaymentId] : null}
        onClose={() => setSelectedPaymentId(null)}
      />
    </div>
  );
}
