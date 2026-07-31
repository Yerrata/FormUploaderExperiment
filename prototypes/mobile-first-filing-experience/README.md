# PROTOTYPE — mobile-first Form C filing experience

## Question

Can a manager operate version 1 primarily from a phone while a separate resort laptop owns the persistent government session and unattended Filing Worker?

This throwaway UI prototype contains fictional data and performs no OCR, document upload, WhatsApp action, government action, or real filing.

## Open

Open `preview.html` directly. No installation or server is required.

The route has three structurally different mobile-first surfaces, switchable with the floating control:

- `?variant=A` — capture-first home and outstanding cases;
- `?variant=B` — chronological case journey;
- `?variant=C` — guided passport-and-visa camera capture.

On a phone, the capture buttons use a file input with `capture="environment"`, allowing a supporting browser to open the rear camera. **Use demo photos** exercises the same state flow without selecting identity documents.

The phone is the Mobile Capture Client. The separate laptop is the Filing Worker and owns credentials, the persistent government session, pre-submit evidence capture, submission, acknowledgement retrieval and Departures reconciliation.
