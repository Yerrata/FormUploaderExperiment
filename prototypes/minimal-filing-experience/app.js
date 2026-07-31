// Three variants of the full Form III filing experience, switchable via ?variant=.

const variantNames = {
  A: "Action-first workspace",
  B: "Chronological journey",
  C: "Exception-first board",
};

const initialCases = [
  {
    id: "YRT-042", guest: "Elena Markovic", initials: "EM", source: "Booking.com", room: "Sea 04",
    checkinDate: "2026-07-31", arrival: "31 Jul, 14:10", checkout: "03 Aug", formB: "B-2026-118",
    status: "needs_guest", step: 1, issue: "Next destination is missing", next: "Collect one missing answer", ack: null,
    fields: { "Passport no.": "P•••••491", Nationality: "Croatia", "Visa no.": "V•••••208", "Visa type": "e-Tourist", "Visa valid until": "19 Oct 2026", "Arrived from": "Chennai", "Next destination": "Missing" },
    messages: [["system", "Welcome to Yeratta Resort. One detail is needed for your government guest registration: where will you travel after Havelock?"]],
  },
  {
    id: "YRT-043", guest: "Daniel Koh", initials: "DK", source: "MakeMyTrip", room: "Garden 02",
    checkinDate: "2026-07-31", arrival: "31 Jul, 15:25", checkout: "02 Aug", formB: "B-2026-119",
    status: "ready", step: 2, issue: null, next: "Open the government form", ack: null,
    fields: { "Passport no.": "E•••••884", Nationality: "Singapore", "Visa no.": "E•••••772", "Visa type": "e-Tourist", "Visa valid until": "06 Sep 2026", "Arrived from": "Port Blair", "Next destination": "Port Blair" },
    messages: [["system", "Your details are complete. We will file the registration automatically."], ["guest", "Thank you"]],
  },
  {
    id: "YRT-044", guest: "Marta Silva", initials: "MS", source: "Walk-in", room: "Palm 01",
    checkinDate: "2026-07-31", arrival: "31 Jul, 16:00", checkout: "05 Aug", formB: "B-2026-120",
    status: "blocked_auth", step: 2, issue: "Government session expired", next: "Renew portal session once", ack: null,
    fields: { "Passport no.": "CA••••615", Nationality: "Portugal", "Visa no.": "I•••••433", "Visa type": "Tourist", "Visa valid until": "28 Nov 2026", "Arrived from": "Port Blair", "Next destination": "Neil Island" },
    messages: [["system", "Your details are complete. Filing is queued while the government session is renewed."]],
  },
  {
    id: "YRT-039", guest: "Noah Williams", initials: "NW", source: "Booking.com", room: "Coral 03",
    checkinDate: "2026-07-30", arrival: "30 Jul, 18:20", checkout: "01 Aug", formB: "B-2026-115",
    status: "verified", step: 5, issue: null, next: "Wait for checkout", ack: "ANI-039-4918",
    fields: { "Passport no.": "53•••••12", Nationality: "Australia", "Visa no.": "AU••••907", "Visa type": "e-Tourist", "Visa valid until": "12 Dec 2026", "Arrived from": "Kolkata", "Next destination": "Port Blair" },
    messages: [["system", "Filing complete. Your acknowledgement has been recorded."]],
  },
  {
    id: "YRT-040", guest: "Aiko Tanaka", initials: "AT", source: "MakeMyTrip", room: "Lagoon 06",
    checkinDate: "2026-07-30", arrival: "30 Jul, 19:05", checkout: "04 Aug", formB: "B-2026-116",
    status: "form_filling", step: 3, issue: null, next: "Fill and validate portal fields", ack: null,
    fields: { "Passport no.": "TR••••144", Nationality: "Japan", "Visa no.": "JP••••533", "Visa type": "e-Tourist", "Visa valid until": "21 Nov 2026", "Arrived from": "Delhi", "Next destination": "Chennai" },
    messages: [["system", "Your details are complete. Filing is in progress."]],
  },
  {
    id: "YRT-046", guest: "Lina Meyer", initials: "LM", source: "Walk-in", room: "Forest 05",
    checkinDate: "2026-08-01", arrival: "01 Aug, 10:30", checkout: "06 Aug", formB: "B-2026-122",
    status: "needs_guest", step: 1, issue: "Arrived-from city is missing", next: "Collect one missing answer", ack: null,
    fields: { "Passport no.": "C7••••218", Nationality: "Germany", "Visa no.": "DE••••601", "Visa type": "Tourist", "Visa valid until": "02 Jan 2027", "Arrived from": "Missing", "Next destination": "Port Blair" },
    messages: [["system", "One detail is needed: which city did you arrive from before Havelock?"]],
  },
];

let cases = structuredClone(initialCases);
let selectedDate = "2026-07-31";
let selectedId = cases[0].id;

function outstandingCases() {
  return cases.filter(item => item.checkinDate === selectedDate && item.status !== "closed");
}

function availableDates() {
  return [...new Set(initialCases.map(item => item.checkinDate))].sort();
}

function selectedCase() {
  const visible = outstandingCases();
  return visible.find(item => item.id === selectedId) || visible[0] || null;
}

function formatDate(date) {
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(`${date}T12:00:00`));
}

function statusMeta(status) {
  return {
    needs_guest: ["Needs guest", "amber"], ready: ["Ready", "blue"], form_filling: ["Portal open", "blue"],
    submitting: ["Submitting", "blue"], verified: ["Filed", "green"], departure_due: ["Departure due", "amber"],
    closed: ["Reconciled", "green"], blocked_auth: ["Session renewal", "red"], blocked_data: ["Blocked", "red"],
  }[status] || [status, "blue"];
}

function badge(item) {
  const [label, tone] = statusMeta(item.status);
  return `<span class="badge ${tone}"><span class="dot"></span>${label}</span>`;
}

function dateFilter() {
  return `<label class="date-filter"><span>Check-in date</span><select data-date>${availableDates().map(date => `<option value="${date}" ${date === selectedDate ? "selected" : ""}>${formatDate(date)}</option>`).join("")}</select></label>`;
}

function summary() {
  const visible = outstandingCases();
  const needs = visible.filter(item => ["needs_guest", "blocked_auth", "blocked_data"].includes(item.status)).length;
  const moving = visible.filter(item => ["ready", "form_filling", "submitting"].includes(item.status)).length;
  const filed = visible.filter(item => ["verified", "departure_due"].includes(item.status)).length;
  return `<section class="summary">
    <div class="metric"><span>Outstanding cases</span><b>${visible.length}</b></div>
    <div class="metric"><span>Needs attention</span><b>${needs}</b></div>
    <div class="metric"><span>Ready or filing</span><b>${moving}</b></div>
    <div class="metric"><span>Filed, not reconciled</span><b>${filed}</b></div>
  </section>`;
}

function header() {
  const renewalNeeded = outstandingCases().some(item => item.status === "blocked_auth");
  return `<header class="topbar">
    <div class="brand"><div class="mark">Y</div><div><strong>Yeratta · Foreign guest filing</strong><span>End-to-end Form C simulation with dummy extraction</span></div></div>
    <div class="top-actions">${dateFilter()}<span class="prototype-flag">Fictional data only</span><span class="health ${renewalNeeded ? "warning" : ""}">● ${renewalNeeded ? "Portal login renewal needed" : "Portal session healthy"}</span></div>
  </header>`;
}

function caseRows(active) {
  const visible = outstandingCases();
  if (!visible.length) return `<div class="empty"><b>No outstanding cases</b><span>All cases for this check-in date are reconciled.</span></div>`;
  return visible.map(item => `<button class="case-row ${item.id === active ? "active" : ""}" data-select="${item.id}">
    <span class="avatar">${item.initials}</span><span><strong>${item.guest}</strong><small>${item.id} · ${item.room}</small></span>${badge(item)}
  </button>`).join("");
}

function fields(item) {
  return `<div class="field-grid">${Object.entries(item.fields).map(([key, value]) => `<div class="field"><span>${key}</span><b>${value}</b></div>`).join("")}</div>`;
}

function chat(item) {
  return `<div class="chat">${item.messages.map(([who, message]) => `<div class="bubble ${who}">${message}</div>`).join("")}</div>`;
}

function evidence(item) {
  return `<div class="evidence">
    <div class="evidence-row"><span>Extraction</span><b>Dummy JSON · validated</b></div>
    <div class="evidence-row"><span>Physical Form B</span><b>${item.formB} · pen-signed</b></div>
    <div class="evidence-row"><span>Submitted values</span><b>${item.step >= 5 ? "Snapshot sealed" : "Not submitted"}</b></div>
    <div class="evidence-row"><span>Acknowledgement</span><b>${item.ack || "Pending"}</b></div>
    <div class="evidence-row"><span>Departures lookup</span><b>${item.status === "closed" ? "Matched" : "Pending"}</b></div>
  </div>`;
}

function callout(item) {
  if (item.status === "needs_guest") return `<div class="callout amber"><b>One guest answer needed</b>${item.issue}. The system asks automatically; staff only handles non-response exceptions.</div>`;
  if (item.status === "blocked_auth") return `<div class="callout red"><b>One-time login boundary</b>The worker cannot bypass or solve CAPTCHA. Staff signs in and completes CAPTCHA once; queued cases resume in the persistent session.</div>`;
  if (item.status === "blocked_data") return `<div class="callout red"><b>Do not submit</b>${item.issue}. Request a clearer image or explicit correction.</div>`;
  if (item.status === "ready") return `<div class="callout green"><b>Ready for unattended filing</b>Critical fields are complete, the physical Form B is linked, and the worker can open Form C.</div>`;
  if (["verified", "departure_due", "closed"].includes(item.status)) return `<div class="callout green"><b>Verified filing</b>Acknowledgement ${item.ack} is linked to the exact submitted-value snapshot.</div>`;
  return `<div class="callout green"><b>Government form automation active</b>The persistent browser worker is filling, checking, and submitting this case.</div>`;
}

function actionText(item) {
  return {
    needs_guest: "Simulate guest reply", ready: "Open simulated government form", form_filling: "Auto-fill and validate",
    submitting: "Submit and capture acknowledgement", verified: "Mark departure due", departure_due: "Reconcile in Departures",
    closed: "Restart this case", blocked_auth: "Simulate staff login + CAPTCHA", blocked_data: "Simulate corrected image",
  }[item.status] || "Simulate next step";
}

function advance(item) {
  if (!item) return;
  if (item.status === "needs_guest") {
    if (item.fields["Next destination"] === "Missing") item.fields["Next destination"] = "Port Blair";
    if (item.fields["Arrived from"] === "Missing") item.fields["Arrived from"] = "Delhi";
    item.messages.push(["guest", item.fields["Next destination"] === "Port Blair" ? "Port Blair" : "Delhi"]);
    item.messages.push(["system", "Thanks. Your details are now complete."]);
    item.status = "ready"; item.step = 2; item.issue = null; item.next = "Open the government form";
  } else if (["blocked_auth", "blocked_data"].includes(item.status)) {
    item.status = "ready"; item.issue = null; item.next = "Open the government form";
  } else if (item.status === "ready") {
    item.status = "form_filling"; item.step = 3; item.next = "Fill and validate portal fields";
  } else if (item.status === "form_filling") {
    item.status = "submitting"; item.step = 4; item.next = "Submit and read portal response";
  } else if (item.status === "submitting") {
    item.status = "verified"; item.step = 5; item.ack = `ANI-${item.id.slice(-3)}-4821`; item.next = "Wait for checkout";
  } else if (item.status === "verified") {
    item.status = "departure_due"; item.step = 6; item.next = "Reconcile in Departures";
  } else if (item.status === "departure_due") {
    item.status = "closed"; item.step = 7; item.next = "Complete";
  } else {
    Object.assign(item, structuredClone(initialCases.find(original => original.id === item.id)));
  }
}

const portalSteps = ["Check session", "Open Form C", "Map fields", "Validate", "Submit", "Capture ack", "Departures match"];

function portalStepIndex(item) {
  return { needs_guest: 0, blocked_data: 0, blocked_auth: 0, ready: 1, form_filling: 3, submitting: 4, verified: 6, departure_due: 6, closed: 7 }[item.status] ?? 0;
}

function governmentPortal(item) {
  const progress = portalStepIndex(item);
  const locked = item.status === "blocked_auth";
  const showValues = ["form_filling", "submitting", "verified", "departure_due", "closed"].includes(item.status);
  const portalFields = [
    ["Full name", item.guest], ["Nationality", item.fields.Nationality], ["Passport number", item.fields["Passport no."]],
    ["Visa number / type", `${item.fields["Visa no."]} · ${item.fields["Visa type"]}`], ["Visa valid until", item.fields["Visa valid until"]],
    ["Arrival / check-in", item.arrival], ["Arrived from", item.fields["Arrived from"]], ["Next destination", item.fields["Next destination"]],
    ["Expected checkout", item.checkout], ["Form B reference", item.formB],
  ];
  return `<article class="gov-panel">
    <div class="gov-head"><div><span class="gov-seal">भारत</span><div><b>External Government Portal</b><small>Form C · simulated browser worker</small></div></div><span class="gov-session ${locked ? "locked" : ""}">${locked ? "Session expired" : "Authenticated session"}</span></div>
    <div class="gov-boundary ${locked ? "blocked" : ""}"><b>${locked ? "Staff action required only here" : "CAPTCHA boundary already passed"}</b><span>${locked ? "A staff member logs in and completes the CAPTCHA. No automated solver or bypass is used." : "The worker reuses the authorised persistent browser session. CAPTCHA is not repeated for each filing."}</span></div>
    <div class="gov-body">
      <ol class="gov-log">${portalSteps.map((step, index) => `<li class="${index < progress ? "done" : index === progress ? "active" : ""}"><span>${index < progress ? "✓" : index + 1}</span><b>${step}</b></li>`).join("")}</ol>
      <div class="gov-form ${locked ? "disabled" : ""}"><div class="gov-form-title"><b>Foreigner registration details</b><span>${showValues ? "Mapped from validated case JSON" : "Waiting for validated case"}</span></div>
        <div class="gov-form-grid">${portalFields.map(([label, value]) => `<label><span>${label}</span><div>${showValues ? value : "—"}</div></label>`).join("")}</div>
        <div class="gov-submit-row"><span>${item.ack ? `Acknowledgement: ${item.ack}` : item.status === "submitting" ? "All required portal fields validated" : "No government action occurs in this prototype"}</span><button disabled>${item.ack ? "Submitted" : "Submit Form C"}</button></div>
      </div>
    </div>
  </article>`;
}

function emptyView() {
  return `<main class="page">${summary()}<section class="panel"><div class="empty large"><b>No outstanding cases for ${formatDate(selectedDate)}</b><span>Select another check-in date or wait for a new case.</span></div></section></main>`;
}

function variantA() {
  const item = selectedCase();
  if (!item) return emptyView();
  return `<main class="page">${summary()}<section class="workspace">
    <aside class="panel"><div class="panel-head"><h2>Outstanding cases</h2><span>${outstandingCases().length}</span></div><div class="case-list">${caseRows(item.id)}</div></aside>
    <section class="stack">
      <article class="panel"><div class="panel-body"><div>${badge(item)}</div><h1 class="action-title">${item.next}</h1><p class="action-copy">${item.guest} · ${item.source} · ${item.room} · Check-in ${formatDate(item.checkinDate)} · Checkout ${item.checkout}</p>${callout(item)}<div class="button-row"><button class="primary" data-advance>${actionText(item)}</button><button class="secondary" data-reset>Reset demo</button></div></div></article>
      ${governmentPortal(item)}
      <article class="panel"><div class="panel-head"><h2>Validated filing values</h2><span class="muted">Dummy extraction JSON</span></div><div class="panel-body">${fields(item)}</div></article>
    </section>
    <aside class="stack">
      <article class="panel"><div class="panel-head"><h3>Guest conversation</h3><span class="muted">WhatsApp simulation</span></div><div class="panel-body">${chat(item)}</div></article>
      <article class="panel"><div class="panel-head"><h3>Evidence</h3></div><div class="panel-body">${evidence(item)}</div></article>
    </aside>
  </section></main>`;
}

const stages = ["Collect", "Validate", "Open portal", "Fill & submit", "Acknowledge", "Departure", "Reconcile"];

function variantB() {
  const item = selectedCase();
  if (!item) return emptyView();
  return `<main class="page"><div class="journey-head"><div><h1>One guest, one clear journey</h1><p class="muted">Outstanding cases checked in on ${formatDate(selectedDate)}.</p></div><div class="case-tabs">${outstandingCases().map(c => `<button class="case-tab ${c.id === item.id ? "active" : ""}" data-select="${c.id}">${c.guest}</button>`).join("")}</div></div>
    <section class="panel"><div class="panel-head"><div><h2>${item.guest} · ${item.id}</h2><span class="muted">${item.source} · ${item.room} · Form B ${item.formB}</span></div>${badge(item)}</div>
      <div class="journey">${stages.map((stage, index) => `<div class="step ${index + 1 < item.step ? "done" : index + 1 === item.step ? "current" : ""}"><div class="step-mark">${index + 1 < item.step ? "✓" : index + 1}</div><h3>${stage}</h3><p>${index + 1 < item.step ? "Complete" : index + 1 === item.step ? item.next : "Waiting"}</p></div>`).join("")}</div>
    </section>
    <section class="journey-detail"><article class="panel"><div class="panel-head"><h2>Current decision</h2></div><div class="panel-body">${callout(item)}<button class="primary" data-advance>${actionText(item)}</button> <button class="secondary" data-reset>Reset demo</button><hr>${fields(item)}</div></article>
    <article class="panel"><div class="panel-head"><h2>Conversation and evidence</h2></div><div class="panel-body">${chat(item)}<hr>${evidence(item)}</div></article></section>
    <div class="portal-wrap">${governmentPortal(item)}</div>
  </main>`;
}

function lane(title, statuses, active) {
  const items = outstandingCases().filter(item => statuses.includes(item.status));
  return `<section class="lane"><div class="lane-title"><span>${title}</span><span>${items.length}</span></div>${items.map(item => `<article class="case-card ${item.id === active ? "active" : ""}" data-select="${item.id}">${badge(item)}<h3>${item.guest}</h3><p>${item.id} · ${item.room}</p><footer><span>${item.next}</span><b>${item.checkout}</b></footer></article>`).join("") || `<p class="muted">No cases</p>`}</section>`;
}

function variantC() {
  const item = selectedCase();
  if (!item) return emptyView();
  return `<main class="page"><div class="board-head"><h1>Outstanding cases by check-in date</h1><p>${formatDate(selectedDate)} · Healthy automation stays quiet; exceptions rise to the left.</p></div>${summary()}<section class="board">
    ${lane("Needs attention", ["needs_guest", "blocked_auth", "blocked_data"], item.id)}
    ${lane("Moving automatically", ["ready", "form_filling", "submitting", "departure_due"], item.id)}
    ${lane("Filed", ["verified"], item.id)}
  </section>
  <section class="drawer"><article class="panel"><div class="panel-head"><h2>${item.guest}</h2>${badge(item)}</div><div class="panel-body">${callout(item)}<button class="primary" data-advance>${actionText(item)}</button> <button class="secondary" data-reset>Reset</button></div></article>
  <article class="panel"><div class="panel-head"><h2>Critical fields</h2></div><div class="panel-body">${fields(item)}</div></article>
  <article class="panel"><div class="panel-head"><h2>Proof</h2></div><div class="panel-body">${evidence(item)}</div></article></section>
  <div class="portal-wrap">${governmentPortal(item)}</div></main>`;
}

function switcher(variant) {
  return `<nav class="variant-switcher"><button data-variant-dir="-1" aria-label="Previous variant">←</button><div class="variant-label">${variant} — ${variantNames[variant]}</div><button data-variant-dir="1" aria-label="Next variant">→</button></nav>`;
}

function currentVariant() {
  const value = new URLSearchParams(location.search).get("variant")?.toUpperCase();
  return variantNames[value] ? value : "A";
}

function setVariant(direction) {
  const keys = Object.keys(variantNames);
  const current = keys.indexOf(currentVariant());
  const next = keys[(current + direction + keys.length) % keys.length];
  const url = new URL(location.href);
  url.searchParams.set("variant", next);
  history.replaceState({}, "", url);
  render();
}

function render() {
  const variant = currentVariant();
  const item = selectedCase();
  if (item) selectedId = item.id;
  const content = variant === "A" ? variantA() : variant === "B" ? variantB() : variantC();
  document.querySelector("#app").innerHTML = `<div class="shell">${header()}${content}</div>${switcher(variant)}`;

  document.querySelectorAll("[data-select]").forEach(element => element.addEventListener("click", () => { selectedId = element.dataset.select; render(); }));
  document.querySelector("[data-advance]")?.addEventListener("click", () => { advance(selectedCase()); render(); });
  document.querySelector("[data-reset]")?.addEventListener("click", () => { cases = structuredClone(initialCases); selectedId = outstandingCases()[0]?.id || ""; render(); });
  document.querySelector("[data-date]")?.addEventListener("change", event => { selectedDate = event.target.value; selectedId = outstandingCases()[0]?.id || ""; render(); });
  document.querySelectorAll("[data-variant-dir]").forEach(element => element.addEventListener("click", () => setVariant(Number(element.dataset.variantDir))));
}

window.addEventListener("keydown", event => {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable) return;
  if (event.key === "ArrowLeft") setVariant(-1);
  if (event.key === "ArrowRight") setVariant(1);
});

window.addEventListener("popstate", render);
render();
