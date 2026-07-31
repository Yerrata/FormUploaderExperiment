# Yeratta Form C filing

Stage 1 is a local-first vertical slice of the agreed Form C workflow. It uses deterministic passport and visa data so the guest experience, JSON hand-off, Filing Worker, mock government form and evidence path can be validated before real document extraction is introduced.

It does not connect to or submit anything to the Indian government portal.

## What works

1. Staff creates a time-limited, single-case Guest Session.
2. The guest photographs passport and visa pages on a phone or tablet.
3. A replaceable dummy extraction adapter creates the candidate identity fields.
4. The guest sees what came from the photographs and can correct it.
5. The wizard asks only missing mandatory questions, one at a time.
6. Confirmation writes one validated `candidate.json` and one immutable `filing-request.json`.
7. The filesystem status moves the case into the Filing Queue.
8. A Python Playwright worker fills the separate mock Form C website.
9. The worker captures and hashes a full-page pre-submit screenshot before clicking submit.
10. A mock acknowledgement and receipt screenshot complete the evidence bundle.

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

The staff case screen starts the Filing Worker as a background task. A separately running watcher is also available:

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
