import axios from "axios";

// Point this at your FastAPI backend. Override with a .env file
// (VITE_API_BASE_URL=http://127.0.0.1:8000) if it runs elsewhere.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});


export async function createBatch(count = 10) {
  const { data } = await client.post(`/batches`, null, { params: { count } });
  return data;
}

export async function runBatch(batchId) {
  const { data } = await client.post(`/batches/${batchId}/run`);
  return data;
}

export async function getMetrics(batchId) {
  const { data } = await client.get(`/metrics/${batchId}`);
  return data;
}

export async function getAudit(batchId) {
  const { data } = await client.get(`/audit`, { params: { batch_id: batchId } });
  return data;
}

export async function getPayments(batchId) {
  const { data } = await client.get(`/payments`, { params: { batch_id: batchId } });
  return data;
}

export async function getPayment(paymentId) {
  const { data } = await client.get(`/payments/${paymentId}`);
  return data;
}

export default client;

