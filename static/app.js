"use strict";

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

async function refreshOperations() {
  const data = await api('/api/operations');
  byId('metric-open').textContent = data.cases.filter(c => c.status === 'open').length;
  byId('delivery-summary').textContent = `${data.jobs.filter(j => j.delivered).length} delivered · ${data.jobs.filter(j => !j.delivered && !j.failed).length} queued · ${data.jobs.filter(j => j.failed).length} exhausted. Notifications are local simulated receipts; the worker handles delivery.`;
  byId('runs').replaceChildren(...data.runs.map(r => el('span', `${r.id} · ${r.result.matched} matched · ${r.result.findings.length} exceptions`)));
  byId('cases').replaceChildren();
  if (!data.cases.length) byId('cases').append(el('p', 'No saved exceptions. Save a settlement investigation to start.'));
  for (const c of data.cases) {
    const card = el('article', undefined, `case ${c.status}`);
    card.append(el('h3', `${c.finding.kind.replaceAll('_', ' ')} · ${c.status}`), el('p', `${c.finding.payment_id} — ${c.finding.detail}`));
    const label = el('label', 'Investigation note');
    const note = el('textarea'); note.id = `note-${c.id}`; label.htmlFor = note.id; note.maxLength = 500; note.rows = 2;
    const button = el('button', c.status === 'open' ? 'Resolve case' : 'Reopen case', 'secondary');
    button.type = 'button';
    button.addEventListener('click', async () => {
      if (note.value.trim().length < 3) { message('Add an investigation note of at least three characters.', true); return; }
      button.disabled = true;
      try {
        await api(`/api/cases/${c.id}`, {method:'PATCH', body:JSON.stringify({status:c.status === 'open' ? 'resolved' : 'open', note:note.value, version:c.version})});
        await refreshOperations(); message('Case decision saved. Payment records are unchanged.');
      } catch (e) {message(e.message, true);} finally {button.disabled = false;}
    });
    const history = el('details'); history.append(el('summary', `Decision history (${c.audit.length})`));
    const list = el('ol'); c.audit.forEach(a => list.append(el('li', `${a.status} · ${new Date(a.created_at * 1000).toLocaleString()} · ${a.note}`))); history.append(list);
    card.append(label, note, button, history); byId('cases').append(card);
  }
}

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
  byId('metric-volume').textContent = money(payments.reduce((sum, p) => sum + p.amount_minor, 0));
  byId('metric-count').textContent = payments.length;
  byId('metric-pending').textContent = payments.filter(p => p.status === 'pending').length;
  byId("payments").replaceChildren();
  for (const payment of payments) {
    if (byId('status-filter').value && payment.status !== byId('status-filter').value) continue;
    if (!(payment.id + ' ' + payment.merchant_reference).toLowerCase().includes(byId('search').value.toLowerCase())) continue;
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
  if (!byId('payments').children.length) {
    const empty = document.createElement("li");
    empty.textContent = 'No matching payments. Explore a sample scenario or create your own.';
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

byId('search').addEventListener('input', () => refresh().catch(e => message(e.message, true)));
byId('status-filter').addEventListener('change', () => refresh().catch(e => message(e.message, true)));
byId('refresh-ops').addEventListener('click', () => refreshOperations().catch(e => message(e.message, true)));
byId('save-run').addEventListener('click', async () => {
  byId('save-run').disabled = true;
  try {
    const result = await api('/api/runs', {method:'POST', body:JSON.stringify({csv:byId('settlement-csv').value})});
    renderComparison(result); await refreshOperations();
    message(result.replayed ? 'Identical file: original saved snapshot returned.' : 'Investigation saved. Review its exceptions below.');
  } catch (e) {message(e.message, true);} finally {byId('save-run').disabled = false;}
});
byId('seed').addEventListener('click', async () => {
  byId('seed').disabled = true;
  try {
    const examples = [['sample-coffee', 125000, 'COFFEE-1042', 'succeeded'], ['sample-books', 89000, 'BOOKS-2081', 'succeeded'], ['sample-market', 245000, 'MARKET-3104', 'pending']];
    const ids = [];
    for (const [key, amount, reference, status] of examples) {
      const result = await api('/api/payments', {method:'POST', headers:{'Idempotency-Key':key}, body:JSON.stringify({amount_minor:amount, currency:'INR', merchant_reference:reference})});
      ids.push(result.payment.id);
      if (status !== 'pending' && result.payment.status === 'pending') await api(`/api/payments/${result.payment.id}/events`, {method:'POST',body:JSON.stringify({event_id:key+'-event',status})});
    }
    await refresh(); await refreshOperations(); await showDetail(ids[0]);
    byId('settlement-csv').value = `payment_id,amount_minor,currency\n${ids[0]},125000,INR\n${ids[1]},88000,INR`;
    message('Scenario ready: two successful payments, one pending, and a ₹10 settlement mismatch. Compare and save an investigation. Repeating the scenario reuses its payment keys.');
  } catch(e) {message(e.message,true);} finally {byId('seed').disabled=false;}
});

(async () => {
  try {
    if (!session) {
      ({token: session} = await api("/api/session", {method: "POST"}));
      sessionStorage.setItem("payment-lab-session", session);
    }
    await refresh();
    await refreshOperations();
    if (payments.length) await showDetail(payments[0].id);
    message("Your isolated demo session is ready.");
  } catch (error) {
    message(error.message, true);
  }
})();
