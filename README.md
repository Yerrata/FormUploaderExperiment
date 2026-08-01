# Yeratta Form C filing

Stage 1 is a local-first vertical slice of the agreed Form C workflow. It uses deterministic passport and visa data so the guest experience and JSON hand-off can be validated before real document extraction is introduced. The current Stage 2 MVP can open and fill the real government Form C from the staff case screen, but it cannot submit the form.

## What works

1. Staff creates a time-limited, single-case Guest Session; hotel arrival time defaults to the current local time and can be corrected before handoff.
2. The guest photographs passport and visa pages on a phone or tablet.
3. A replaceable dummy extraction adapter creates the candidate identity fields.
4. The guest sees what came from the photographs and can correct it.
5. The wizard asks only missing guest-sourced Form C questions, one at a time. It never asks for hotel arrival time, room, the locked property address or the unproven Form B/Filer reference.
6. Confirmation writes one validated `candidate.json` and one immutable `filing-request.json`.
7. The filesystem status moves the case into the Filing Queue.
8. Staff chooses **Open portal and fill Form C**; the app creates one self-contained fill plan and applies it immediately.
9. The worker stops only when the live page cannot perform a planned control operation.
10. Staff reviews the live form and the government portal owns final data validation. The automation contains no submission action.

There is no database, cloud backend, message broker, automated WhatsApp integration or real Optical Character Recognition (OCR).

## Local setup

```bash
python -m venv .venv
.venv/bin/pip install -e '.[test]'
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers .venv/bin/playwright install chromium
```

Playwright is pinned to version 1.56 because the current Yeratta laptop runs macOS 13. Newer Playwright browser bundles no longer support that operating-system target.

Start the application:

```bash
.venv/bin/formc-app --host 0.0.0.0 --port 8000 --data-dir data
```

Open `http://127.0.0.1:8000/staff` on the Filing Worker. A phone on the same trusted Yeratta Wi-Fi can open `http://<filing-worker-ip>:8000/staff`.

The staff case screen is the primary MVP workflow. Once a guest has completed the Filing Request:

1. Open the case from the staff dashboard.
2. Choose **Open portal and fill Form C**.
3. Complete the normal government login and CAPTCHA in the dedicated Chromium window when asked.
4. Review the filled live form and submit it manually only when it is correct. The app neither clicks Submit nor captures the acknowledgement yet.

The old mock worker remains available only for Stage 1 development and regression testing. Do not run its watcher while testing the live staff workflow:

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers .venv/bin/formc-worker \
  --base-url http://127.0.0.1:8000 \
  --data-dir data \
  --watch
```

## Test

```bash
.venv/bin/pytest -q
```

The automated suite checks the guest journey, mandatory-field blocking, correction provenance, single-case token isolation and expiry, atomic JSON persistence, duplicate worker claims, mock-portal idempotency, safe retry and evidence creation.

## Data layout

```text
data/
  cases/
    YRT-20260731-AB12/
      metadata.json
      status.json
      candidate.json
      filing-request.json
      documents/
        passport.jpg
        visa.jpg
      evidence/
        manifest.json
        pre-submit-attempt-1.png
        acknowledgement-attempt-1.png
  mock_submissions/
```

Writes use a temporary file, disk flush and atomic rename. A worker claim is represented by an atomically created `worker.lock` directory. A case whose submission outcome is uncertain is never placed back in the ready queue automatically.

## Deployment boundary

Stage 1 stores sensitive test documents locally. Before using real guest documents, the Filing Worker must have operating-system full-disk encryption enabled, such as FileVault on macOS or BitLocker on Windows, a locked staff account and an encrypted backup. Application retention and deletion controls are completed before the live Stage 2 pilot.

The guest link grants access to one case only. It becomes read-only immediately after the guest creates the Filing Request. Government credentials and the real authenticated portal are deliberately absent from Stage 1.

## Stage 2 preview: authorised portal login

The first Stage 2 component uses a dedicated persistent Chromium profile for the government portal. It does not bypass CAPTCHA, fill a live form or submit anything. Staff completes the normal login and CAPTCHA once; the helper reports ready only after it detects a plausible authenticated Form C form on the official HTTPS host.

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers .venv/bin/formc-portal-login
```

If the portal gave staff a fresh signed Form C URL, pass it only for that run:

```bash
FORMC_PORTAL_URL='https://indianfrro.gov.in/frro/FormC/formc.jsp?...' \
  PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers \
  .venv/bin/formc-portal-login
```

The browser profile is stored under `data/portal-browser-profile/` and should be accessible only to Yeratta's Filing Worker account. `data/portal-session.json` records readiness without saving the URL query or browser cookies.

On the Yeratta portal, the authenticated state does not survive closing and reopening Chromium. Therefore, catalogue the live form structure in the same browser process as login:

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers \
  .venv/bin/formc-portal-login --catalogue
```

Staff completes the normal login and CAPTCHA, then the catalogue runs immediately before that browser closes. The future Filing Worker will likewise remain alive from Portal Session Renewal through authorised processing; a worker restart requires renewal.

The catalogue is read-only. It does not fill, click or submit controls. It stores names, IDs, types, labels, select options and static radio/checkbox choice codes in the gitignored `data/portal-controls.json`; it excludes current text/file values, hidden inputs, credential-like controls, cookies, page HTML, screenshots, form actions and URL queries. The explicit Candidate mapping and its fail-closed gaps are documented in `docs/stage-2-control-mapping.md`. Live submission remains disabled.

The field registry separates unconditional Form C readiness, conditionally required portal branches, internal hotel metadata and optional fields. Staff supplies check-in date and hotel arrival time; expected checkout also comes from staff or booking data when known and falls back to one guest question only when absent. Room stays in case metadata, and the legacy physical Form B reference is no longer collected by the MVP. Every additional question backed by a closed Candidate choice or usable captured portal options is rendered as a dropdown. Closed sex, employment, purpose-of-visit and destination-scope answers are normalised and translated to their exact portal codes; portal-owned choices retain the exact captured option label used by the fill plan. A separate guest-camera photograph is converted to a portal-safe JPEG. Intended stay is derived as the number of days between check-in and checkout when those dates can be interpreted. Fill-plan creation does not block e-Visa labels, outside-India destinations, conditional branches or other business values; the live control or government portal reports what it cannot accept.

Yeratta's India reference address is Filing Worker configuration, not a guest answer. Create the gitignored `data/property.json` locally with the portal's exact state and district option codes:

```json
{
  "reference_address": "LOCAL YERATTA REFERENCE ADDRESS",
  "reference_state_code": "PORTAL STATE OPTION VALUE",
  "reference_district_code": "PORTAL DISTRICT OPTION VALUE",
  "reference_pin_code": "000000"
}
```

Replace every placeholder locally. Do not commit the real property configuration. When this file is present, its values are copied into the fill plan. A missing or invalid file no longer blocks opening and filling the portal; the corresponding controls remain untouched for staff or portal validation.

Build the self-contained fill plan directly for diagnostic use with:

```bash
.venv/bin/python -m formc_app.fill_plan YRT-YYYYMMDD-XXXX --data-dir data
```

This command only writes `data/cases/<case-id>/fill-plan.json` and its SHA-256 seal. It copies available Candidate, photograph and property values into ordered control operations. It does not compare those values with `portal-controls.json`, reject unsupported business values or open a browser.

The staff case screen prepares the plan automatically and starts fill-only without case-specific terminal commands. The underlying diagnostic command remains available for developers:

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers \
  .venv/bin/formc-fill-only YRT-YYYYMMDD-XXXX --data-dir data
```

The staff action opens the official portal in the dedicated Chromium profile and waits for normal staff login and CAPTCHA when necessary. The executor verifies only the plan seal, ordered operation structure, safe control identifiers and the permanent no-submit boundary. It then locates each live control and performs the requested fill, selection, radio check or upload. If the page cannot perform an operation, the run stops and reports that exact source field and portal control. Otherwise the filled page remains open for staff review. The executor contains no submit action and refuses both known submission controls.
