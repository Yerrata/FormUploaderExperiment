# Authorised Form III route verification

## Outcome

Yeratta Resort reports verbal confirmation by phone from the responsible official that:

- unattended browser submission using the resort's authorised account is permitted;
- the existing physical Form B register signature made with pen satisfies the guest-signature requirement; and
- the portal acknowledgement number is sufficient filing evidence.

Written confirmation was not obtained. Authorised local observations established that CAPTCHA appears only at login, not at final submission; the session survives browser restart and normally persists until logout; and acknowledgement numbers remain retrievable through Departures.

The accepted version-1 route is a persistent local browser worker. Rare staff Portal Session Renewal is permitted when authentication expires, but staff never handle an individual filing.

## Safety boundary

Do not place portal credentials, CAPTCHA values, guest identity data, session tokens, or unredacted screenshots in GitHub, email, or chat. Use only the resort's authorised account and genuine operational records. Do not submit synthetic guest data, create deliberate duplicates, inspect hidden endpoints, use third-party CAPTCHA solving, or bypass access controls.

## Verified operating behaviour

- CAPTCHA: login only.
- Final submission: no additional CAPTCHA.
- Session: survives full browser restart and normally lasts until explicit logout.
- Success proof: government acknowledgement number.
- Later verification: acknowledgement remains available in Departures.
- Guest signature: existing physical Form B register signed with pen.
- Account maintenance: rare Portal Session Renewal is acceptable; per-filing human action is not.

## Architecture decision rule

The route is acceptable only while all of the following remain true:

- the persistent authorised session can submit and verify filings without staff handling individual cases;
- loss of authentication is detected before submission and cases queue safely;
- staff are asked only for Portal Session Renewal;
- exact submitted values and the acknowledgement number form a tamper-evident Evidence Package;
- acknowledgements are reconciled later against Departures;
- the Form B register entry is linked to the electronic case; and
- no CAPTCHA solving, credential sharing, access-control bypass, or hidden endpoint use occurs.

If portal behaviour or official direction changes so that every filing requires human authentication or confirmation, the mandatory Fully Unattended Submission requirement becomes a no-go until an authorised route is restored.
