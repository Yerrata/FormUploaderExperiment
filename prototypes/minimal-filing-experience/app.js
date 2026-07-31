// Three variants of the full Form III filing experience, switchable via ?variant=.

const variantNames = {
  A: "Action-first workspace",
  B: "Chronological journey",
  C: "Exception-first board",
};

const initialCases = [
  {
    id: "YRT-042",
    guest: "Elena Markovic",
    initials: "EM",
    source: "Booking.com",
    room: "Sea 04",
    arrival: "31 Jul, 14:10",
    checkout: "03 Aug",
    formB: "B-2026-118",
    status: "needs_guest",
    step: 1,
    issue: "Next destination is missing",
    next: "Send one WhatsApp question",
    ack: null,
    fields: {
      "Passport no.": "P•••••491",
      Nationality: "Croatia",
      "Visa no.": "V•••••208",
      "Visa valid until": "19 Oct 2026",
      "Arrived from": "Chennai",
      "Next destination": "Missing",
    },
    messages: [
      ["system", "Welcome to Yeratta Resort. One detail is needed for your government guest registration: where will you travel after Havelock?"],
    ],
  },
  {
    id: "YRT-043",
    guest: "Daniel Koh",
    initials: "DK",
    source: "MakeMyTrip",
    room: "Garden 02",
    arrival: "31 Jul, 15:25",
    checkout: "02 Aug",
    formB: "B-2026-119",
    status: "ready",
    step: 2,
    issue: null,
    next: "Submit automatically",
    ack: null,
    fields: {
      "Passport no.": "E•••••884",
      Nationality: "Singapore",
      "Visa no.": "E•••••772",
      "Visa valid until": "06 Sep 2026",
      "Arrived from": "Port Blair",
      "Next destination": "Port Blair",
    },
    messages: [
      ["system", "Your details are complete. We will file the registration automatically."],
      ["guest", "Thank you"],
    ],
  },
  {
    id: "YRT-044",
    guest: "Marta Silva",
    initials: "MS",
    source: "Walk-in",
    room: "Palm 01",
    arrival: "31 Jul, 16:00",
    checkout: "05 Aug",
    formB: "B-2026-120",
    status: "blocked_auth",
    step: 2,
    issue: "Government session expired",
    next: "Renew portal session once",
    ack: null,
    fields: {
      "Passport no.": "CA••••615",
      Nationality: "Portugal",
      "Visa no.": "I•••••433",
      "Visa valid until": "28 Nov 2026",
      "Arrived from": "Port Blair",
      "Next destination": "Neil Island",
    },
    messages: [
      ["system", "Your details are complete. Filing is queued while the government session is renewed."],
    ],
  },
];

let cases = structuredClone(initialCases);
let selectedId = cases[0].id;

function selectedCase() {
  return cases.find(item => item.id === selectedId) || cases[0];
}

function statusMeta(status) {
  return {
    needs_guest: ["Needs guest", "amber"],
    ready: ["Ready", "blue"],
    submitting: ["Submitting", "blue"],
    verified: ["Filed", "green"],
    departure_due: ["Departure due", "amber"],
    closed: ["Reconciled", "green"],
    blocked_auth: ["Session renewal", "red"],
    blocked_data: ["Blocked", "red"],
  }[status] || [status, "blue"];
}

function badge(item) {
  const [label, tone] = statusMeta(item.status);
  return `<span class="badge ${tone}"><span class="dot"></span>${label}</span>`;
}

function summary() {
  const needs = cases.filter(item => ["needs_guest", "blocked_auth", "blocked_data"].includes(item.status)).length;
  const ready = cases.filter(item => ["ready", "submitting"].includes(item.status)).length;
  const filed = cases.filter(item => ["verified", "departure_due", "closed"].includes(item.status)).length;
  return `<section class="summary">
    <div class="metric"><span>Today’s foreign guests</span><b>${cases.length}</b></div>
    <div class="metric"><span>Needs attention</span><b>${needs}</b></div>
    <div class="metric"><span>Ready or filing</span><b>${ready}</b></div>
    <div class="metric"><span>Verified filings</span><b>${filed}</b></div>
  </section>`;
}

function header() {
  return `<header class="topbar">
    <div class="brand"><div class="mark">Y</div><div><strong>Yeratta · Foreign guest filing</strong><span>Form III prototype with dummy extraction</span></div></div>
    <div class="top-actions"><span class="prototype-flag">Fictional data only</span><span class="health">● Portal session healthy</span></div>
  </header>`;
}

function caseRows(active) {
  return cases.map(item => `<button class="case-row ${item.id === active ? "active" : ""}" data-select="${item.id}">
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
    <div class="evidence-row"><span>Form B register</span><b>${item.formB}</b></div>
    <div class="evidence-row"><span>Submitted values</span><b>${item.step >= 3 ? "Snapshot sealed" : "Not submitted"}</b></div>
    <div class="evidence-row"><span>Acknowledgement</span><b>${item.ack || "Pending"}</b></div>
    <div class="evidence-row"><span>Departure reconciliation</span><b>${item.status === "closed" ? "Matched" : "Pending"}</b></div>
  </div>`;
}

function callout(item) {
  if (item.status === "needs_guest") return `<div class="callout amber"><b>One guest answer needed</b>${item.issue}. The system asks automatically; staff does nothing.</div>`;
  if (item.status === "blocked_auth") return `<div class="callout red"><b>Portal session renewal required</b>Cases are queued safely. Staff logs in once; the system resumes automatically.</div>`;
  if (item.status === "blocked_data") return `<div class="callout red"><b>Do not submit</b>${item.issue}. Request a clearer image or explicit correction.</div>`;
  if (item.status === "ready") return `<div class="callout green"><b>Ready for unattended filing</b>All Critical Fields are complete and the Form B entry is linked.</div>`;
  if (["verified", "departure_due", "closed"].includes(item.status)) return `<div class="callout green"><b>Verified Filing</b>Acknowledgement ${item.ack} is linked to the submitted values.</div>`;
  return `<div class="callout green"><b>Submission in progress</b>The persistent browser worker is checking the final portal state.</div>`;
}

function actionText(item) {
  return {
    needs_guest: "Simulate guest reply",
    ready: "Simulate submission",
    submitting: "Capture acknowledgement",
    verified: "Mark departure due",
    departure_due: "Reconcile departure",
    closed: "Restart this case",
    blocked_auth: "Simulate session renewal",
    blocked_data: "Simulate corrected image",
  }[item.status] || "Simulate next step";
}

function advance(item) {
  if (item.status === "needs_guest") {
    item.fields["Next destination"] = "Port Blair";
    item.messages.push(["guest", "Port Blair"]);
    item.messages.push(["system", "Thanks. Your details are now complete."]);
    item.status = "ready"; item.step = 2; item.issue = null; item.next = "Submit automatically";
  } else if (item.status === "blocked_auth") {
    item.status = "ready"; item.issue = null; item.next = "Submit automatically";
  } else if (item.status === "blocked_data") {
    item.status = "ready"; item.issue = null; item.next = "Submit automatically";
  } else if (item.status === "ready") {
    item.status = "submitting"; item.step = 3; item.next = "Verify portal response";
  } else if (item.status === "submitting") {
    item.status = "verified"; item.step = 4; item.ack = `ANI-${item.id.slice(-3)}-4821`; item.next = "Wait for checkout";
  } else if (item.status === "verified") {
    item.status = "departure_due"; item.step = 5; item.next = "Update departure automatically";
  } else if (item.status === "departure_due") {
    item.status = "closed"; item.step = 6; item.next = "Complete";
  } else {
    Object.assign(item, structuredClone(initialCases.find(original => original.id === item.id)));
  }
}

function variantA() {
  const item = selectedCase();
  return `<main class="page">${summary()}<section class="workspace">
    <aside class="panel"><div class="panel-head"><h2>Today’s cases</h2><span>${cases.length}</span></div><div class="case-list">${caseRows(item.id)}</div></aside>
    <section class="stack">
      <article class="panel"><div class="panel-body"><div>${badge(item)}</div><h1 class="action-title">${item.next}</h1><p class="action-copy">${item.guest} · ${item.source} · ${item.room} · Checkout ${item.checkout}</p>${callout(item)}<div class="button-row"><button class="primary" data-advance>${actionText(item)}</button><button class="secondary" data-reset>Reset demo</button></div></div></article>
      <article class="panel"><div class="panel-head"><h2>Validated filing values</h2><span class="muted">Dummy extraction JSON</span></div><div class="panel-body">${fields(item)}</div></article>
    </section>
    <aside class="stack">
      <article class="panel"><div class="panel-head"><h3>Guest conversation</h3><span class="muted">WhatsApp simulation</span></div><div class="panel-body">${chat(item)}</div></article>
      <article class="panel"><div class="panel-head"><h3>Evidence</h3></div><div class="panel-body">${evidence(item)}</div></article>
    </aside>
  </section></main>`;
}

const stages = ["Input", "Validate", "Submit", "Acknowledge", "Departure", "Reconcile"];

function variantB() {
  const item = selectedCase();
  return `<main class="page"><div class="journey-head"><div><h1>One guest, one clear journey</h1><p class="muted">Follow the case from check-in to departure reconciliation.</p></div><div class="case-tabs">${cases.map(c => `<button class="case-tab ${c.id === item.id ? "active" : ""}" data-select="${c.id}">${c.guest}</button>`).join("")}</div></div>
    <section class="panel"><div class="panel-head"><div><h2>${item.guest} · ${item.id}</h2><span class="muted">${item.source} · ${item.room} · Form B ${item.formB}</span></div>${badge(item)}</div>
      <div class="journey">${stages.map((stage, index) => `<div class="step ${index + 1 < item.step ? "done" : index + 1 === item.step ? "current" : ""}"><div class="step-mark">${index + 1 < item.step ? "✓" : index + 1}</div><h3>${stage}</h3><p>${index + 1 < item.step ? "Complete" : index + 1 === item.step ? item.next : "Waiting"}</p></div>`).join("")}</div>
    </section>
    <section class="journey-detail"><article class="panel"><div class="panel-head"><h2>Current decision</h2></div><div class="panel-body">${callout(item)}<button class="primary" data-advance>${actionText(item)}</button> <button class="secondary" data-reset>Reset demo</button><hr style="border:0;border-top:1px solid var(--line);margin:18px 0">${fields(item)}</div></article>
    <article class="panel"><div class="panel-head"><h2>Conversation and evidence</h2></div><div class="panel-body">${chat(item)}<hr style="border:0;border-top:1px solid var(--line);margin:18px 0">${evidence(item)}</div></article></section>
  </main>`;
}

function lane(title, statuses, active) {
  const items = cases.filter(item => statuses.includes(item.status));
  return `<section class="lane"><div class="lane-title"><span>${title}</span><span>${items.length}</span></div>${items.map(item => `<article class="case-card ${item.id === active ? "active" : ""}" data-select="${item.id}">${badge(item)}<h3>${item.guest}</h3><p>${item.id} · ${item.room}</p><footer><span>${item.next}</span><b>${item.checkout}</b></footer></article>`).join("") || `<p class="muted">No cases</p>`}</section>`;
}

function variantC() {
  const item = selectedCase();
  return `<main class="page"><div class="board-head"><h1>Only show what needs a decision</h1><p>Healthy automation stays quiet. Exceptions rise to the left.</p></div>${summary()}<section class="board">
    ${lane("Needs attention", ["needs_guest", "blocked_auth", "blocked_data"], item.id)}
    ${lane("Moving automatically", ["ready", "submitting", "departure_due"], item.id)}
    ${lane("Verified", ["verified", "closed"], item.id)}
  </section>
  <section class="drawer"><article class="panel"><div class="panel-head"><h2>${item.guest}</h2>${badge(item)}</div><div class="panel-body">${callout(item)}<button class="primary" data-advance>${actionText(item)}</button> <button class="secondary" data-reset>Reset</button></div></article>
  <article class="panel"><div class="panel-head"><h2>Critical Fields</h2></div><div class="panel-body">${fields(item)}</div></article>
  <article class="panel"><div class="panel-head"><h2>Proof</h2></div><div class="panel-body">${evidence(item)}</div></article></section></main>`;
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
  const content = variant === "A" ? variantA() : variant === "B" ? variantB() : variantC();
  document.querySelector("#app").innerHTML = `<div class="shell">${header()}${content}</div>${switcher(variant)}`;

  document.querySelectorAll("[data-select]").forEach(element => element.addEventListener("click", () => { selectedId = element.dataset.select; render(); }));
  document.querySelector("[data-advance]")?.addEventListener("click", () => { advance(selectedCase()); render(); });
  document.querySelector("[data-reset]")?.addEventListener("click", () => { cases = structuredClone(initialCases); render(); });
  document.querySelectorAll("[data-variant-dir]").forEach(element => element.addEventListener("click", () => setVariant(Number(element.dataset.variantDir))));
}

window.addEventListener("keydown", event => {
  if (["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable) return;
  if (event.key === "ArrowLeft") setVariant(-1);
  if (event.key === "ArrowRight") setVariant(1);
});

window.addEventListener("popstate", render);
render();

