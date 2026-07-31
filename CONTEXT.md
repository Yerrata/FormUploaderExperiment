# Form C Filing

This context describes how a foreign guest's check-in particulars become an authorised Indian Form C filing while keeping guest participation separate from Yeratta's filing authority.

## Language

**Form C Filing**:
One completed government submission of a foreign guest's required stay and identity particulars.
_Avoid_: Application, policy filing

**Guest Session**:
A time-limited, single-case interaction in which one guest supplies and confirms particulars on a Yeratta-managed device.
_Avoid_: Guest account, open kiosk session

**Guest Input**:
Identity documents or answers supplied directly by the guest during a Guest Session.
_Avoid_: Staff intervention, voluntary data

**Guest-Corrected Field**:
A Critical Field for which the guest rejected the extracted candidate and supplied a replacement while the original value and its provenance remain recorded.
_Avoid_: Verified field, OCR overwrite

**Candidate Form C**:
The normalised, not-yet-filed set of required particulars, document provenance and validation outcomes for one guest stay.
_Avoid_: Form C submission, extracted JSON

**Filing Request**:
A guest-confirmed request for Yeratta to file one Candidate Form C; it does not itself carry government submission authority.
_Avoid_: Guest submission, submit Form C

**Filing Queue**:
The ordered collection of accepted Filing Requests awaiting authorised processing.
_Avoid_: Remaining candidates queue, submission queue

**Filing Worker**:
The Yeratta-controlled actor that owns the authorised government portal session and processes Filing Requests.
_Avoid_: Guest app, capture client

**Fully Unattended Submission**:
A property-selected mode in which a Supported Case proceeds through government submission without human handling of that individual filing.
_Avoid_: The entire guest-to-filing workflow, automation requiring per-case staff action

**Human-reviewed Submission**:
A property-selected mode in which the Filing Worker fills a Supported Case and an authorised human reviews the live government form before submitting it.
_Avoid_: Guest review, guest submission

**Portal Session Renewal**:
The authorised human login and CAPTCHA step required when the government portal session is no longer valid, performed independently of any guest case.
_Avoid_: CAPTCHA bypass, per-case approval

**Critical Field**:
A required identity, travel or stay value whose incorrect value could misidentify the guest or make the filing materially incorrect.
_Avoid_: A field accepted only because an extraction confidence threshold was exceeded

**Supported Case**:
A Candidate Form C whose required particulars are present, internally consistent, backed by supported documents and within the validated filing rules.
_Avoid_: Any captured case, best-effort case

**Filing Evidence Bundle**:
The tamper-evident history linking source particulars, submitted values, submission attempts, government acknowledgement and reconciliation state for one guest stay.
_Avoid_: Receipt, screenshot-only proof, evidence package

**Verified Filing**:
A Form C Filing whose government acceptance and submitted values are supported by its Filing Evidence Bundle.
_Avoid_: A successful click, request sent, HTTP success response
