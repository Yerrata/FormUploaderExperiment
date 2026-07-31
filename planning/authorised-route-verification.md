# Authorised Form III route verification

## Purpose

Resolve whether Yeratta Resort can submit Form III filings and departure updates without staff action through an authorised government route.

Do not place portal credentials, CAPTCHA values, guest identity data, session tokens, or unredacted screenshots in GitHub, email, or chat. Use only the resort's authorised account and genuine operational records. Do not submit synthetic guest data, intentionally create duplicates, inspect hidden endpoints, solve CAPTCHA through a third party, or bypass an access control.

## Local portal observation

Open the official [Form III login](https://indianfrro.gov.in/frro/FormC/login.jsp) from the resort's normal connection and record only behaviour and field names.

### Authentication

- CAPTCHA location: login only, session renewal, each filing, departure update, or another event.
- Session lifetime: normal use, idle timeout, browser restart, and password change.
- Whether a lawful authenticated session survives long enough for unattended queued filings.
- Whether concurrent sessions are allowed.
- Any notices or conditions concerning automation, integration, or account use.

### Filing workflow

Using the next genuine filing, record:

- every arrival and departure field, mandatory marker, format rule, and validation message;
- how guest signature is captured, stored, displayed, and inspected;
- save-draft behaviour;
- the final submission step;
- the exact success state and stable government identifier;
- any printable/downloadable filed record;
- the filed-history view;
- correction or amendment behaviour;
- how a naturally occurring retry, timeout, or duplicate warning is handled.

Do not deliberately trigger duplicate or invalid government submissions.

### Filing Evidence

Determine which official artefact proves acceptance:

- acknowledgement or reference number;
- filed-record view;
- printable/downloadable Form III;
- receipt;
- another authoritative status.

A locally generated “request sent” message or screenshot is not sufficient by itself.

### Su-Swagatam

Using an authorised device/account, establish whether the current Indian Visa Su-Swagatam application provides an accommodation-keeper Form III workflow and whether that route avoids repeated human authentication. Do not assume that visitor-facing features support hotel filing.

## Written official enquiry

Send the same enquiry to:

- the resort's responsible South Andaman Foreigners Registration Officer, using the official contact already associated with its accommodation registration; and
- the portal's published technical-support address: `nic-frmcadm@nic.in`.

### Suggested subject

Authorised unattended Form III integration and electronic-signature clarification for Yeratta Resort

### Draft

Yeratta Resort is registered to file accommodation Form III particulars for foreign guests. We are planning a system that collects and validates the required particulars and then submits arrival and departure information through an authorised government channel.

Please confirm the following in writing:

1. Is an official API, bulk-upload facility, PMS/channel-manager integration, service account, IP allowlisting arrangement, or other machine-to-machine route available for Form III arrival and departure filing?
2. If no API exists, is unattended browser automation using the resort's own authorised account permitted? If so, what approval, security, session, CAPTCHA, or operational conditions apply?
3. Does Indian Visa Su-Swagatam currently support Form III submission by accommodation keepers, and is any integration interface available?
4. Rule 17 requires the foreign guest's signature on arrival. May the resort capture a signature on a touchscreen and retain it electronically with the guest's Form III particulars? If yes, what signature format, consent wording, timestamp, identity linkage, retention, and inspection requirements apply? Is another signature method required?
5. What portal-generated acknowledgement or record should the resort retain as authoritative evidence of successful arrival and departure transmission?
6. Are there any current technical specifications, notices, integration guidelines, or approval forms that the resort should follow?

The proposed system will not use CAPTCHA-solving services, bypass access controls, or share credentials. We would appreciate the correct technical and jurisdictional contact if these questions should be directed elsewhere.

## Decision rule

The mandatory Fully Unattended Submission requirement passes only if at least one route is both:

- authorised in writing or expressly documented by the responsible authority; and
- technically able to submit, verify, and retain Filing Evidence without recurring staff action.

If every authorised route requires a person to complete CAPTCHA, sign in, or confirm each filing, fully unattended version 1 is not feasible under the accepted constraint. The architecture must report this as a no-go decision rather than conceal a manual step.
