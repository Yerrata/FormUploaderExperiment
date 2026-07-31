# PROTOTYPE — minimal Form C filing experience

## Question

Which desktop layout makes the complete Yeratta Resort Form C filing workflow easiest to understand and operate when passport and visa extraction is temporarily replaced by deterministic dummy JSON?

This is a throwaway, read-only usability prototype. It contains fictional data and simulates WhatsApp, extraction, an external government Form C, acknowledgements, session renewal, and departure updates. It performs no real external action.

The government portal simulation makes the CAPTCHA boundary explicit: automation does not solve or bypass it. If the persistent authorised session expires, staff signs in and completes CAPTCHA once. Queued cases then resume unattended through field mapping, validation, submission, acknowledgement capture, and Departures reconciliation.

The workspace shows outstanding cases—not only today's cases—filtered by a selectable check-in date.

The chronological journey is the selected direction and is now the default view. Before any simulated submission, the worker captures a full-page portal image and canonical field JSON, records the timestamp and integrity hash, and seals that evidence. Submission remains a separate later step.

For a direct, dependency-free preview, open `preview.html`. It contains the CSS and JavaScript inline so file-preview environments do not need to load sibling assets.

## One command

```bash
python -m http.server 8080 --directory prototypes/minimal-filing-experience
```

Then open:

- `http://localhost:8080/?variant=A` — action-first workspace
- `http://localhost:8080/?variant=B` — chronological journey (selected/default)
- `http://localhost:8080/?variant=C` — exception-first board

Use the floating arrow switcher or keyboard left/right arrows to compare variants. Select a check-in date and fictional case, then press the primary action repeatedly to move it through guest correction, validation, government-form entry, submission, acknowledgement, departure, and reconciliation states.
