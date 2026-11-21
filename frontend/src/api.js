// Single place the UI talks to the backend. Contract: API_CONTRACT.md.
// Set VITE_USE_MOCKS=true to serve the synthetic JSON in ./mocks instead of calling the API,
// so UI work never blocks on the backend.
import comparison from "./mocks/comparison.json";
import intake from "./mocks/intake.json";
import match from "./mocks/match.json";
import rfq from "./mocks/rfq.json";
import quotation from "./mocks/quotation.json";
import shortlist from "./mocks/shortlist.json";
import approval from "./mocks/approval.json";

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

export const mocks = { intake, match, rfq, quotation, comparison, shortlist, approval };

// Error envelope: { error: { code, message, details[], request_id } }
export class ApiError extends Error {
  constructor(error, status) {
    super(error?.message || `HTTP ${status}`);
    this.code = error?.code || "UNKNOWN";
    this.details = error?.details || [];
    this.status = status;
  }
}

export async function request(method, path, body) {
  const isForm = body instanceof FormData;
  const res = await fetch(path, {
    method,
    headers: body && !isForm ? { "Content-Type": "application/json" } : undefined,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error, res.status);
  return data;
}

export const getHealth = () => request("GET", "/api/health");
