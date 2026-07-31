# Guest and booking data channels for Form C version 1

Research date: 31 July 2026  
Scope: one property, WhatsApp-first guest intake, optional Booking.com and MakeMyTrip enrichment, no hard OTA runtime dependency.

## Decision

Use a **WhatsApp Cloud API conversation as the primary guest entry point**, backed by a **single-use secure web capture link** for guests who cannot use WhatsApp and for image-quality retries. Create a case from a booking notification, PMS/channel-manager event, or a minimal staff entry; never wait for a Booking.com or MakeMyTrip API before starting or filing a case.

For version 1, prefer booking data in this order:

1. an existing PMS/channel manager integration, if Yeratta Resort already uses one and its API/webhook terms permit this use;
2. automatic ingestion of official booking emails/vouchers into a dedicated mailbox;
3. a minimal staff-created case containing guest contact and stay dates.

Direct Booking.com Connectivity API access and a direct MakeMyTrip accommodation API are not dependable version-1 assumptions. Treat every imported booking field as a convenience hint: reconcile it against document extraction and guest answers, record its source, and never overwrite a higher-authority value silently.

## WhatsApp Business Platform: viable and bounded

### What works

Meta's Cloud API is the official hosted WhatsApp Business Platform API. It supports programmatic and human/bot conversations and backend integrations. Meta requires a business portfolio, WhatsApp Business Account (WABA), and business phone number. The official collection lists the `whatsapp_business_management` and `whatsapp_business_messaging` permissions; production should use a system-user token rather than the 24-hour test user token. The app must subscribe to the WABA for message/status webhooks. Phone registration requires ownership verification and a six-digit two-step-verification PIN. [Meta's official Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api)

Inbound text, image and document messages are delivered through webhooks. Incoming media messages contain a media ID that the service can retrieve, so passport and visa images can enter the extraction pipeline without staff copying files. Outbound delivery status is also webhook-driven. [Meta media](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/media), [messages webhook](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages), [webhook overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview)

The cleanest session start is a QR code or `wa.me` link at booking/check-in that causes the guest to message the resort. Each user message opens or refreshes a 24-hour customer-service window in which free-form service replies are permitted. Outside that window, the resort must use an approved template. Templates must be approved before sending, and businesses must obtain WhatsApp opt-in before proactive messaging. A phone number present in an OTA booking should **not** be treated automatically as WhatsApp opt-in. [Service-message rules](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages), [template fundamentals](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview), [opt-in](https://developers.facebook.com/documentation/business-messaging/whatsapp/getting-opt-in)

Create a small set of utility templates: pre-arrival invitation, missing-information reminder, image-retake request, filing-success confirmation, and blocked-case notice. Keep the actual questionnaire state in the application, not in chat history. Ask one short question at a time, accept structured buttons where suitable, and always show the extracted value when requesting a correction.

### Cost and onboarding constraints

Meta charges by delivered message, recipient market and category. As of the research date, service messages and utility messages sent in response to a user are free; proactive utility templates can be chargeable. Meta has announced that **all service messages become per-message chargeable on 1 October 2026**, at market-based rates, so version 1 must meter outbound messages and use the live rate card during budgeting rather than assume a lasting free allowance. [Current official pricing](https://whatsappbusiness.com/products/platform-pricing/), [announced October 2026 change](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages)

For one resort, onboard the resort directly in Meta Business Manager and Cloud API; Embedded Signup is useful mainly when a solution provider onboards many customer businesses. Complete phone ownership, display-name/WABA setup, billing, production token and webhook verification before considering the channel ready. Use a Business Solution Provider only if direct onboarding/support becomes the blocker, because it may add fees and another processor.

### Document handling constraints

WhatsApp is a transport, not the document system of record. On receiving media, immediately bind it to the correct case, verify the declared guest/session, download it to encrypted private storage, hash it, log provenance, and apply the case retention/deletion policy. Do not expose permanent object URLs or retain access tokens in logs. If image checks fail, send a reason-specific retake request and the secure camera link.

## Secure web capture fallback

Send a random, single-use, short-expiry case link only through the guest's active WhatsApp thread or verified booking contact. It should require no reusable password, reveal minimal case data before verification, and become invalid after completion or expiry. OWASP recommends cryptographically random, securely stored, single-use and expiring URL tokens. [OWASP token guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)

The page should use HTTPS/HSTS, guided camera capture for passport photo page and visa, an image preview, short missing-field form, and explicit submission confirmation. Allow-list JPEG/PNG/PDF only where needed; check actual file type rather than trusting `Content-Type`; generate server-side filenames; enforce size limits; store outside the webroot; and malware-scan uploads. [OWASP file-upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), [OWASP TLS guidance](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)

## Booking.com: do not build a direct dependency in version 1

Booking.com's Connectivity APIs can retrieve reservations and messages, but they are for approved Connectivity Partners. Booking.com expects such providers to satisfy onboarding requirements, support broad API functionality, work with PMS partners, load a year of rates/availability, maintain their integration, and coordinate through a Connectivity Account Manager. This is disproportionate for a new single-property Form C helper. [Connectivity API overview and partner expectations](https://developers.booking.com/connectivity/docs)

An approved provider can poll the Reservations API for new/modified/cancelled reservations and acknowledge them; Booking.com explicitly says reservations are pulled rather than pushed by webhook. Unacknowledged reservations fall back to property email. [Retrieving reservations](https://developers.booking.com/connectivity/docs/reservations-api/retrieving-new-reservations-ota), [polling and fallback behaviour](https://developers.booking.com/connectivity/docs/con-faq-reservations-missing-res-messages), [Reservations overview](https://developers.booking.com/connectivity/docs/reservations-api/reservations-overview)

Therefore:

- If the resort already has an approved PMS/channel manager, consume its authorized reservation webhook/API.
- Otherwise parse Booking.com reservation emails in a dedicated mailbox and keep Extranet as the human verification source.
- Revisit direct Connectivity access only after Booking.com confirms eligibility; do not automate Extranet login or scrape its pages.

## MakeMyTrip/Goibibo: channel manager or notifications, not an assumed public API

Go-MMT's official partner materials provide an Extranet/Connect app with booking lists, stay dates, guest/booker name, room, booking ID, contact information, messages and downloadable/email vouchers. New bookings are notified by email and SMS, in the app, and optionally WhatsApp for pending confirmations. [Booking details](https://partners.go-mmt.com/support/solutions/articles/81000408580-how-can-i-check-the-bookings-that-i-have-received-for-my-property-), [notifications](https://partners.go-mmt.com/support/solutions/articles/81000197207-how-will-i-be-notified-of-my-bookings-other-than-the-extranet-), [vouchers](https://partners.go-mmt.com/support/solutions/articles/81000408592-where-can-i-find-all-my-booking-vouchers-)

The public hotel-partner route documented by Go-MMT is a channel manager: select a supported provider in Extranet, after which Go-MMT generates an access token for that hotel/provider connection. The official support site says more than 80 channel managers are available. [Channel-manager mapping](https://partners.go-mmt.com/support/solutions/articles/81000197192-how-can-i-map-my-property-s-channel-manager-with-ingo-mmt-extranet-), [channel-manager options](https://partners.go-mmt.com/support/solutions/folders/81000143618)

No first-party public accommodation-reservation API suitable for a hotel's bespoke one-property integration was found. MakeMyTrip's published `myBiz` APIs serve corporate travel-request and expense integrations, not hotel-supplier reservation ingestion. Consequently, version 1 should use an existing approved channel manager if present; otherwise ingest emailed vouchers/notifications. Guest contact availability may be limited until three days before check-in, so the workflow must also support staff entering a phone number obtained lawfully at arrival. [Go-MMT guest-contact timing](https://partners.go-mmt.com/support/solutions/articles/81000279001-how-can-i-contact-guests-who-have-already-made-a-booking-for-my-property-), [myBiz integration scope](https://mybiz.makemytrip.com/integrated-travel-solutions)

## Channel patterns to carry forward

1. **Recommended: WhatsApp session + secure capture bridge + optional booking enrichment.** Highest practical reach, controlled image retries, no OTA availability dependency, and almost no staff work on normal cases.
2. **Pure WhatsApp intake.** Fastest to prototype, but weaker capture guidance and a larger sensitive-data footprint; keep only as a supported path, not the sole path.
3. **Web-first intake with WhatsApp reminders.** Strongest upload/security control and useful fallback, but greater guest drop-off; retain for non-WhatsApp guests and correction loops.

Version-1 readiness gates are: production WABA and phone verified; approved utility templates; opt-in/session-start design tested; webhook retries and idempotency proven; secure upload threat model passed; retention/deletion agreed; dedicated OTA mailbox or existing PMS feed connected; and every imported field visibly provenance-tagged.
