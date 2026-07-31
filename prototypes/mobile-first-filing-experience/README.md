# PROTOTYPE — phone-only Form C filing experience

## Question

Can a manager complete the full Form C workflow on one Android phone: capture documents, retain the government session, fill the form, review and submit it, capture the acknowledgement and reconcile Departures?

This throwaway UI prototype contains fictional data and performs no OCR, document upload, government action or real filing.

## Open

Open `preview.html` directly. No installation or server is required.

The preview opens on Outstanding Cases. Tap **Government login needed**, **Open login →** or **Government site** to open the expired-session example. Enter mock CAPTCHA `4261`.

The route has three mobile-first surfaces:

- `?variant=A` — capture-first home and outstanding cases;
- `?variant=B` — chronological case with Tasks and Government site tabs;
- `?variant=C` — guided passport-and-visa camera capture.

Every operation is owned by the same phone. In production this implies a dedicated Android app with an in-app government browser: a normal web page cannot safely control a separately opened government page or retain its authenticated session. Login and CAPTCHA remain manual on the phone. After that, the app fills the government form locally, seals pre-submit evidence and opens the filled form for manager review.

The task pane cannot submit. It only opens the filled government form. The manager must review it and tap **I checked it — Submit Form C** on the government page. The app then captures the acknowledgement, links it to the pre-submit evidence and uses it for Departures reconciliation.

After the snapshot is sealed, **Pre-submit evidence sealed** becomes a link in the task timeline. Tapping it opens the government page and shows the evidence ID, pre-submission timing and linked case.

On a supporting phone browser, the capture input uses `capture="environment"` to open the rear camera. **Use demo photo** exercises the same prototype flow without selecting identity documents. Dummy JSON replaces passport extraction until the end-to-end usability is accepted.

After the two photos, the prototype now stops on **Review what the phone read**. It displays every candidate Form C value together with its source: Passport photo, Visa photo, Booking, guest answer or staff entry. The same candidate-data card remains visible in **Data & tasks**, and the mock government page is filled from the same data structure so the values can be compared directly.
