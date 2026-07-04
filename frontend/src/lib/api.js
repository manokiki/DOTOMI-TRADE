/**
 * Client API DOTOMI-TRADE — Version complète.
 * Tous les endpoints backend, anciens et nouveaux.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Erreur ${res.status} sur ${path}`);
  }
  return res.json();
}

export const api = {
  // Health
  health:        ()           => request("/health"),
  healthMarkets: ()           => request("/health/markets"),
  healthSystem:  (h = 24)     => request(`/health/system?hours=${h}`),

  // Scanner
  scan:    (symbol, tf)       => request(`/scanner?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(tf)}`),
  scanAll: (tf = "1h")        => request(`/scanner/all?timeframe=${tf}`),

  // Recommendations
  topRecommendation: ()       => request("/recommendations/top"),

  // Macro
  getMacro: ()                => request("/macro"),

  // Risk
  getRiskSummary: (capital)   => request(`/risk/summary${capital ? `?capital=${capital}` : ""}`),
  computeSizing:  (data)      => request("/risk/sizing", { method: "POST", body: JSON.stringify(data) }),
  getCapitalCurve: ()         => request("/capital/curve"),

  // Human Check-in
  createCheckIn:   (data)     => request("/human/checkin", { method: "POST", body: JSON.stringify(data) }),
  getTodayCheckIn: ()         => request("/human/checkin/today"),

  // Validation
  validateSetup: (setupId)    => request(`/setup/validate?setup_id=${setupId}`, { method: "POST" }),

  // Trades
  openTrade:  (data)          => request("/trade/open", { method: "POST", body: JSON.stringify(data) }),
  closeTrade: ({ tradeId, exitPrice, note, errorTag }) => {
    const p = new URLSearchParams({ trade_id: tradeId, exit_price: exitPrice });
    if (note)     p.append("note", note);
    if (errorTag) p.append("error_tag", errorTag);
    return request(`/trade/close?${p}`, { method: "POST" });
  },

  // Journal
  journal: (limit = 50)       => request(`/journal?limit=${limit}`),

  // Historique Système
  systemSignals: ({ limit = 100, status, symbol } = {}) => {
    const p = new URLSearchParams({ limit });
    if (status) p.append("status", status);
    if (symbol) p.append("symbol", symbol);
    return request(`/system/signals?${p}`);
  },

  // Analytics
  analytics: ()               => request("/analytics"),
};
