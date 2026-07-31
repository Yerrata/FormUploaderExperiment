# PROTOTYPE — mobile-first Form C filing experience

## Question

Can a manager operate version 1 primarily from a phone while a separate resort laptop owns the persistent government session and unattended Filing Worker?

This throwaway UI prototype contains fictional data and performs no OCR, document upload, WhatsApp action, government action, or real filing.

## Open

Open `preview.html` directly. No installation or server is required.

The preview opens directly on Outstanding Cases. Tap **Government site** or **Laptop needs login** to open the expired-session example with the mock login and CAPTCHA visible. Use the floating arrows to reach the other surfaces.

**Laptop needs login** has two large tap targets on Outstanding Cases: the persistent header status and an explicit **Open login →** alert. Both open the same mock CAPTCHA screen.

The Outstanding Cases surface keeps **Outstanding cases** and **Government site** tabs visible at every viewport width. Every visible control has a working demo result: worker status, tabs, date filter, case rows, camera capture and reset. Opening Government site selects the active session-renewal case when one exists, making the login and CAPTCHA immediately reachable.

The government pane is a local mock external website. Enter CAPTCHA `4261`, then use its action button to run the worker and seal pre-submit evidence. At that point the task pane can only open the filled government form: the manager must review it and click **I checked it — Submit Form C** on the government page. The prototype then captures the acknowledgement automatically. Departures lookup and reconciliation remain available from the government pane.

In production, the live authenticated government browser remains on the filing laptop. The mobile application can request and report work, but it must not copy the login session or attempt to embed the government site. This prototype uses the right pane to represent the real-browser handoff.

After the snapshot is sealed, **Pre-submit evidence sealed** becomes a link in the task timeline. Tapping it opens the government pane and shows the evidence ID, its pre-submission timing and the linked case.

The route has three structurally different mobile-first surfaces, switchable with the floating control:

- `?variant=A` — capture-first home and outstanding cases;
- `?variant=B` — chronological two-pane case journey;
- `?variant=C` — guided passport-and-visa camera capture.

On a phone, the capture buttons use a file input with `capture="environment"`, allowing a supporting browser to open the rear camera. **Use demo photos** exercises the same state flow without selecting identity documents.

The phone is the Mobile Capture Client. The separate laptop is the Filing Worker and owns credentials, the persistent government session, pre-submit evidence capture, submission, acknowledgement retrieval and Departures reconciliation.

The chronological case surface uses exactly two panes on laptop and tablet: automation tasks on the left and the changing government site on the right. On a phone, the same panes become **Tasks** and **Government site** tabs so the government form remains readable; starting a portal-affecting task automatically opens the government-site tab.
