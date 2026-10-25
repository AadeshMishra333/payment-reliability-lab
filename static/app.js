"use strict";

const byId = id => document.getElementById(id);
let session = sessionStorage.getItem("payment-lab-session");
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
  const {payments} = await api("/api/payments");
  byId("payments").replaceChildren();
  for (const payment of payments) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = `${payment.merchant_reference} · ${money(payment.amount_minor)}`;
    const detail = document.createElement("span");
    detail.textContent = `${payment.id} · ${payment.status}`;
    item.append(title, detail);
    byId("payments").append(item);
  }
  if (!payments.length) {
    const empty = document.createElement("li");
    empty.textContent = "No payments in this demo session yet.";
    byId("payments").append(empty);
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
    message(result.replayed ? `Retry returned existing ${result.payment.id}; no second payment was created.` : `Created ${result.payment.id} as a pending synthetic payment.`);
  } catch (error) {
    message(error.message, true);
  } finally {
    byId("submit").disabled = false;
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
    message("Your isolated demo session is ready.");
  } catch (error) {
    message(error.message, true);
  }
})();
