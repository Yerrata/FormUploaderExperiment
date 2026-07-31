# PROTOTYPE — minimal end-to-end Form C demo

## Question

Can the complete operator experience be demonstrated with one human CAPTCHA login followed by unattended fake-government-form filing, pre-submit evidence capture, acknowledgement capture, and departure reconciliation?

Yes. This throwaway prototype uses fictional guest data and an embedded fake government portal. It performs no real government, WhatsApp, booking-channel, or filing action.

## Run

Open `demo.html` directly in a modern desktop browser. No installation or server is required.

## Demo sequence

1. In the external portal panel, enter the displayed CAPTCHA and choose **Login once**.
2. Select an outstanding case by check-in date.
3. Choose **Run unattended filing**.
4. Watch the worker fill and validate the separate portal form, seal a PNG plus canonical JSON before submission, submit, and capture the acknowledgement.
5. Choose **Reconcile departure** to complete the case through the portal's Departures section.

The browser worker is simulated with messages to a separate embedded portal document. Production implementation would replace that adapter with authorised persistent-browser automation. CAPTCHA solving or bypass is explicitly out of scope.
