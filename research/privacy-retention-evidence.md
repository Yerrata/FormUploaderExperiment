# Privacy, signature, retention and evidence obligations

**Status date:** 31 July 2026. This is architecture research, not legal advice. Local counsel and the jurisdictional Registration Officer/FRO should confirm the open points below.

## Decision

Version 1 must treat Yeratta Resort as the controller of a high-risk identity-data workflow. Keep the signed electronic accommodation record, submitted Form III data, departure update and Filing Evidence together for **at least one year**; make them immediately retrievable for inspection. Do not assume that the law requires a one-year copy of every passport/visa image: the 2025 immigration rule expressly requires the *particulars* to be retained, not the source scans or a portal receipt. Raw-image retention therefore needs a separate, short policy until the DPDP one-year processing-retention rule takes effect or local authority confirms otherwise.

Use Indian-region storage and processors under written data-processing terms. Preserve original government acknowledgements plus hashes and an audit trail; a screenshot alone is weaker evidence. A guest must actually sign the arrival record. Fully unattended filing is not legally safe until the Registration Officer confirms which electronic-signature method satisfies rule 17.

## Binding now

### Immigration filing and hotel record

Rule 17 of the [Immigration and Foreigners Rules, 2025](https://www.mha.gov.in/sites/default/files/2025-09/Immigration_and_Foreigners_Rules_2025_16092025.pdf) applies to every foreign guest, including an OCI cardholder. The accommodation keeper must:

- obtain the required particulars and the foreigner's signature on arrival;
- obtain departure date/time and the address or destination to which the guest proceeds;
- maintain those particulars electronically for **at least one year**, continuously available on demand to the Registration Officer, District Magistrate or police officer of at least Head Constable rank;
- transmit completed Form III electronically through the designated portal/app no later than 24 hours after arrival; and
- transmit departure details no later than 24 hours after departure.

The departure deadline runs from **actual departure**, not the booking's planned checkout. Automation therefore needs a reliable actual-checkout event and deadline monitor. The [A&N Administration's official notice of 23 October 2025](https://dt.andamannicobar.gov.in/epaper/10232025.pdf) repeats these duties and identifies the South Andaman Superintendent of Police as FRO. Under the [2026 compounding notification](https://www.mha.gov.in/sites/default/files/2026-01/7._Notification_regarding_compounding_of_certain_offences_under_the_Immigration_and_Foreigners_Act%2C_2025_20012026.pdf), non-submission under section 8/rule 17 may be compounded at ₹50,000 per case.

Form III, explicitly labelled “Earlier Form C,” includes a photograph, premises/contact details, name as in passport, nationality, passport number, visa/OCI number and type, Indian contact, email, arrival source/time/purpose/previous stay, and departure time/next destination. Rule 17 defines “sign” to include a thumb impression or customary mark for a person unable to write. It does **not** specify touchscreen, OTP, drawn-signature or certified e-sign mechanics. Form III itself has no guest-signature field, so the signature belongs to the keeper's underlying accommodation record.

No provision found in these Rules expressly requires retaining passport/visa scans or the portal acknowledgement, or attaching the acknowledgement to the visa. Those are operational evidence choices unless another local rule applies.

### Current data-protection baseline

Until the main DPDP duties commence, section 43A of the [Information Technology Act, 2000](https://www.indiacode.nic.in/handle/123456789/1999) and the [Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011](https://upload.indiacode.nic.in/showfile?actid=AC_CEN_45_76_00001_200021_1517807324077&filename=GSR313E_10511%281%29_0.pdf&type=rule) remain the operational private-sector baseline. A passport/visa image and guest answers are personal information. They become SPDI where, for example, facial patterns are measured for authentication; ordinary OCR alone does not necessarily make the photograph “biometric.”

For direct guest collection, the Rules require a published privacy policy, collection notice, written consent for SPDI, lawful necessity and purpose limitation, a review/correction route, no longer retention than the lawful purpose requires, reasonable security, and a named grievance officer responding within one month. SPDI disclosure needs permission unless contractually agreed or legally required. Overseas transfer requires the recipient to provide the same protection level and be necessary for the lawful contract or consented to. MeitY's [official applicability clarification](https://www.pib.gov.in/newsite/erelcontent.aspx?relid=74990) confirms that direct providers remain subject to Rules 5 and 6.

The 2011 Rules require a documented security programme with controls proportionate to the data; ISO/IEC 27001 is one recognised route. Section 43A creates compensation exposure where negligent safeguards cause wrongful loss/gain.

### Cyber incidents and evidence

The [CERT-In directions of 28 April 2022](https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf) cover body corporates. They require a CERT-In point of contact, specified cyber incidents—including data breaches/leaks—to be reported within six hours of notice, and ICT logs to be securely retained for a rolling 180 days. The direction says logs are to be maintained in Indian jurisdiction; use an Indian copy even though the later FAQ permits overseas storage if prompt production is possible.

Electronic records have the same legal effect as other documents subject to section 63 of the [Bharatiya Sakshya Adhiniyam, 2023](https://upload.indiacode.nic.in/view-casepdf?id=AC_CEN_5_23_00049_2023-47_1719292804654&type=act). Its computer-output certificate records the system/source and hash. This does not mandate hashing every filing, but strongly supports preserving originals, provenance and hashes if Filing Evidence must later be proved.

## DPDP transition

The [DPDP commencement notification, G.S.R. 843(E)](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf) and [final DPDP Rules, G.S.R. 846(E)](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf) phase obligations:

- Already effective: Act definitions and institutional/Board provisions; Rules 1, 2 and 17–21.
- **14 November 2026:** consent-manager provisions.
- **14 May 2027:** core processing duties in Act sections 3–17 and Rules 3, 5–16, 22 and 23.

Therefore DPDP access, erasure, processor-contract, security and breach duties are **not yet binding on 31 July 2026**, but version 1 should be designed for them. From 14 May 2027 the resort is likely the Data Fiduciary and cloud/OCR/messaging vendors its Data Processors. The resort remains accountable; processors require valid contracts; data disclosed to government must be complete, accurate and consistent. Required controls include notice and lawful basis, access/correction/erasure subject to legal retention, security safeguards, processor security clauses, affected-person notice without delay, Board notice without delay plus details within 72 hours, and verifiable parental consent for children.

Rule 8(3) will require personal data, traffic data and processing logs to be retained for **at least one year from processing** for specified State-access purposes, then erased unless another law requires longer. Its breadth appears to include raw images sent to OCR; obtain legal confirmation before the effective date. Cross-border processing is generally allowed subject to government restrictions/orders; no blanket DPDP localisation rule was found, but Significant Data Fiduciary and other laws can impose localisation.

## Required architecture controls

1. Separate raw uploads, signed accommodation record, submitted payload, portal response, departure update and audit logs; give each a versioned retention rule.
2. Encrypt transport/storage; least-privilege access; MFA; secret isolation; Indian log copy; no production identity data in analytics, model training or support transcripts.
3. Filing Evidence should contain the original acknowledgement/download, portal transaction/reference, submitted-field snapshot, arrival/departure timestamps, retrieval metadata and SHA-256 hashes in an append-only audit trail.
4. Processor contracts must restrict purpose and model training, list locations/subprocessors, require confidentiality and equivalent safeguards, rapid incident escalation within the resort's six-hour CERT-In window, deletion/return, rights-request help, audit evidence and exportability.
5. Issue a concise guest notice covering legal filing, vendors, retention and contact/complaint routes. Collect separate consent only for processing beyond the legal filing purpose.

## Local confirmation blockers

- Which arrival-signature method does the Andaman Registration Officer accept, and is a departure signature also expected?
- Do UT police, tourism, tax or hotel-register rules require passport/visa copies or retention longer than one year?
- What acknowledgement does the current portal issue, and can it be reliably downloaded later?
- Does the Registration Officer regard electronically retained particulars plus signature evidence as sufficient for on-demand inspection?
- How should the future DPDP one-year rule be reconciled with early deletion of raw identity scans?
