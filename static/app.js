"use strict";

const byId = id => document.getElementById(id);
let session = sessionStorage.getItem("payment-lab-session");
let payments = [];
let selectedPaymentId = null;
const money = minor => new Intl.NumberFormat("en-IN", {style: "currency", currency: "INR"}).format(minor / 100);

function message(text, error = false) {
  byId("message").textContent = text;
  byId("message").classList.toggle("error", error);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {"Content-Type": "application/json", ...(session ? {"X-Demo-Session": session} : {}), ...options.headers},
  });
  const result = await response.json();
  if (!response.ok) {
    const detail = typeof result.detail === "string" ? result.detail : "Check the input and try again.";
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  return result;
}

async function refresh() {
  ({payments} = await api("/api/payments"));
  byId("payments").replaceChildren();
  for (const payment of payments) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.addEventListener("click", () => showDetail(payment.id));
    const title = document.createElement("strong");
    title.textContent = `${payment.merchant_reference} · ${money(payment.amount_minor)}`;
    const detail = document.createElement("span");
    detail.textContent = `${payment.id} · ${payment.status}`;
    button.append(title, detail);
    item.append(button);
    byId("payments").append(item);
  }
  if (!payments.length) {
    const empty = document.createElement("li");
    empty.textContent = "No payments in this demo session yet.";
    byId("payments").append(empty);
  }
}

async function showDetail(paymentId) {
  try {
    const {payment, events} = await api(`/api/payments/${encodeURIComponent(paymentId)}`);
    selectedPaymentId = payment.id;
    byId("selected").hidden = false;
    byId("selected-heading").textContent = `${payment.merchant_reference}: ${payment.status}`;
    byId("selected-id").textContent = payment.id;
    byId("events").replaceChildren();
    for (const event of events) {
      const item = document.createElement("li");
      item.textContent = `${event.event_id}: ${event.status} (${event.applied ? "state changed" : "no state change"})`;
      byId("events").append(item);
    }
    if (!events.length) {
      const item = document.createElement("li");
      item.textContent = "No simulated events yet.";
      byId("events").append(item);
    }
  } catch (error) {
    message(error.message, true);
  }
}

async function sendEvent(status) {
  if (!selectedPaymentId) return;
  const eventId = byId("event-id").value.trim();
  if (!/^[A-Za-z0-9_-]{1,80}$/.test(eventId)) {
    message("Use an event ID containing letters, numbers, hyphens or underscores.", true);
    return;
  }
  const buttons = ["mark-success", "mark-failed", "send-pending"].map(byId);
  buttons.forEach(button => button.disabled = true);
  try {
    const result = await api(`/api/payments/${encodeURIComponent(selectedPaymentId)}/events`, {
      method: "POST", body: JSON.stringify({event_id: eventId, status}),
    });
    await refresh();
    await showDetail(selectedPaymentId);
    message(result.replayed ? `Duplicate event ${eventId} ignored; payment remains ${result.payment.status}.` :
      result.applied ? `Event ${eventId} changed payment to ${result.payment.status}.` :
      `Event ${eventId} recorded; payment remains ${result.payment.status}.`);
  } catch (error) {
    message(error.message, true);
  } finally {
    buttons.forEach(button => button.disabled = false);
  }
}

function renderComparison(result) {
  byId("comparison-summary").textContent = `${result.rows} settlement row(s), ${result.matched} matched, ${result.findings.length} exception(s). Scope: ${result.scope}.`;
  byId("findings").replaceChildren();
  if (!result.findings.length) {
    const item = document.createElement("li");
    item.textContent = "No exceptions found.";
    byId("findings").append(item);
  }
  for (const finding of result.findings) {
    const item = document.createElement("li");
    const kind = document.createElement("strong");
    kind.textContent = finding.kind.replaceAll("_", " ");
    const detail = document.createElement("span");
    detail.textContent = `${finding.payment_id}: ${finding.detail}`;
    item.append(kind, detail);
    byId("findings").append(item);
  }
}

byId("payment-form").addEventListener("submit", async event => {
  event.preventDefault();
  const raw = byId("amount").value.trim();
  if (raw === "0" || /^0+(\.0{1,2})?$/.test(raw)) {
    message("Enter an amount greater than ₹0.00.", true);
    return;
  }
  if (!/^\d+(\.\d{1,2})?$/.test(raw)) {
    message("Enter a positive amount with at most two decimal places.", true);
    return;
  }
  const [rupees, paise = ""] = raw.split(".");
  const amountMinor = Number(rupees) * 100 + Number(paise.padEnd(2, "0"));
  if (!Number.isSafeInteger(amountMinor) || amountMinor < 1 || amountMinor > 10_000_000) {
    message("Enter an amount between ₹0.01 and ₹100,000.00.", true);
    return;
  }
  const reference = byId("reference").value.trim();
  if (!reference) {
    message("Enter a merchant reference.", true);
    return;
  }
  const requestKey = byId("request-key").value.trim();
  if (!/^[A-Za-z0-9_-]{1,80}$/.test(requestKey)) {
    message("Use a request key containing letters, numbers, hyphens or underscores.", true);
    return;
  }
  byId("submit").disabled = true;
  try {
    const result = await api("/api/payments", {method: "POST", headers: {"Idempotency-Key": requestKey}, body: JSON.stringify({amount_minor: amountMinor, currency: "INR", merchant_reference: reference})});
    await refresh();
    await showDetail(result.payment.id);
    message(result.replayed ? `Retry returned existing ${result.payment.id}; no second payment was created.` : `Created ${result.payment.id} as a pending synthetic payment.`);
  } catch (error) {
    message(error.message, true);
  } finally {
    byId("submit").disabled = false;
  }
});

byId("mark-success").addEventListener("click", () => sendEvent("succeeded"));
byId("mark-failed").addEventListener("click", () => sendEvent("failed"));
byId("send-pending").addEventListener("click", () => sendEvent("pending"));

byId("fill-sample").addEventListener("click", () => {
  byId("settlement-csv").value = ["payment_id,amount_minor,currency", ...payments.filter(payment => payment.status === "succeeded").map(payment => `${payment.id},${payment.amount_minor},INR`)].join("\n");
  message("Sample file filled from successful payments in this session. Edit a value to test an exception.");
});

byId("compare").addEventListener("click", async () => {
  byId("compare").disabled = true;
  try {
    const result = await api("/api/reconcile", {method: "POST", body: JSON.stringify({csv: byId("settlement-csv").value})});
    renderComparison(result);
    message("Settlement comparison complete. No payment state was changed.");
  } catch (error) {
    message(error.message, true);
  } finally {
    byId("compare").disabled = false;
  }
});

byId("new-key").addEventListener("click", () => {
  byId("request-key").value = `req-${crypto.randomUUID().slice(0, 8)}`;
  message("New request key ready. Submitting now creates a separate operation.");
});

(async () => {
  try {
    if (!session) {
      ({token: session} = await api("/api/session", {method: "POST"}));
      sessionStorage.setItem("payment-lab-session", session);
    }
    await refresh();
    if (payments.length) await showDetail(payments[0].id);
    message("Your isolated demo session is ready.");
  } catch (error) {
    message(error.message, true);
  }
})();
