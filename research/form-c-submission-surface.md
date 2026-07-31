# Authorised Form III (legacy Form C) submission surface

Research date: 31 July 2026  
Scope: official Indian government material and publicly accessible official portal pages only.

## Decision

**A lawful, reliable, fully unattended version 1 is not yet demonstrated.** The government provides two authorised electronic destinations—the designated FRRO portal and, in law, the Indian Visa Su-Swagatam mobile application—but no public official documentation located in this research describes an accommodation-provider API, bulk interface, partner integration, machine account, allowlisting programme, or CAPTCHA-free service account.

The public Form III portal places an image CAPTCHA at sign-in. Without an official machine interface, a written automation authorisation/exception, or evidence that an authorised session can be maintained and renewed unattended, fresh or expired sessions cannot be guaranteed to submit without a person. CAPTCHA solving or bypass is outside the permissible design.

Therefore the architecture may automate intake, extraction, validation, queuing and evidence handling now, but **government submission must remain a version-1 feasibility gate** until the resort completes an authorised-account observation and obtains an official answer about unattended integration.

## Verified facts

### Current legal obligation and workflow

The controlling instrument is the **Immigration and Foreigners Rules, 2025**, effective from 1 September 2025 and superseding the Registration of Foreigners Rules, 1992. What hotels commonly call “Form C” is now **Form III, Earlier Form C**. See [Rules 1 and Form III](https://www.mha.gov.in/sites/default/files/2025-09/Immigration_and_Foreigners_Rules_2025_16092025.pdf).

Rule 17 requires every keeper of accommodation to:

1. obtain the required particulars from every foreigner, **including an OCI cardholder**;
2. obtain the foreigner’s signature on arrival and, at departure, the departure date/time and destination address;
3. maintain those particulars electronically for at least one year and keep them available for official inspection;
4. transmit the arrival Form III electronically no later than 24 hours after arrival; and
5. transmit departure details electronically no later than 24 hours after departure.

The permitted destinations named in Rule 17 are the designated online portal or the mobile application referred to by Rule 12: [https://indianfrro.gov.in](https://indianfrro.gov.in) and “Indian Visa Su-Swagatam.” The underlying statutory obligation is in section 8 of the [Immigration and Foreigners Act, 2025](https://www.indiacode.nic.in/bitstream/123456789/21918/1/A2025-13.pdf).

The current official Form III requires:

- premises name/address and phone/mobile;
- photograph;
- full passport name, nationality and passport number;
- visa number or OCI number and visa type;
- Indian contact phone, email and other details/remarks;
- arrived-from location, arrival date/time, purpose of visit and previous place of stay;
- departure date/time and next destination.

This is the legally published field set. The authenticated portal may impose additional fields or validation; that cannot be established from the public form.

### Account and authentication surface

The public [Form III/Form II login page](https://indianfrro.gov.in/frro/FormC/login.jsp) exposes user-ID/password login plus an image challenge labelled “Refresh Image” and “Type the code shown above.” It also instructs users to change their password every 30 days. Its current notice confirms Form III/Form C applies to all foreigners including OCI cardholders.

The same official service exposes [accommodation-user registration](https://indianfrro.gov.in/frro/FormC/accom_reg.jsp), a [print/reprint registration-request menu](https://indianfrro.gov.in/frro/FormC/menuuserreg.jsp), and CAPTCHA-protected recovery/activation surfaces such as [forgot password](https://indianfrro.gov.in/frro/FormC/forgot_pwd.jsp) and [individual-house OTP activation](https://indianfrro.gov.in/frro/FormC/otp.jsp).

What is verified is CAPTCHA **at login and selected account-management operations**. Public pages do not establish whether another CAPTCHA appears per filing, how long a login session lasts, whether sessions can be renewed without a CAPTCHA, or how concurrent sessions behave.

### Validation and filing evidence

The 2025 Rules require electronic transmission but do not prescribe a receipt format, acknowledgement number, printable certificate, or attachment to a visa. The unauthenticated official pages do not document success/error states, server-side validation, duplicate handling, correction/amendment, retries, or a filing-history export.

Accordingly, a browser reaching a final button is not acceptable proof of filing. Version 1 needs an authenticated observation to identify the government-generated success artefact—such as an acknowledgement ID, immutable filed-record view, downloadable/printable Form III, or another authoritative status—and to define failure states. If the portal supplies none, the resort must agree an evidence standard with its jurisdictional FRO; locally generated screenshots alone should not be treated as government acknowledgement.

No official source found requires a Form III receipt to be attached physically to the guest’s visa. The law does require the resort’s signed electronic accommodation record to be retained for at least one year.

## Authorised machine routes

The 2025 Rules expressly permit submission through the portal **or** Indian Visa Su-Swagatam. This makes the mobile application an authorised channel in principle. However, the official public [Indian Visa service](https://indianvisaonline.gov.in/) and the NIC [app listing](https://play.google.com/store/apps/details?id=org.nic.ivfrt.visitindia) describe visitor-facing visa/FRRO features; they do not publicly document a keeper-of-accommodation Form III workflow or an integration interface. Its actual Form III availability must be tested with the resort’s authorised identity/device.

No public official material located in targeted searches documents:

- an API or webhook for Form III;
- CSV/XML/JSON or other bulk upload;
- PMS/OTA partner integration;
- service/machine credentials;
- IP allowlisting or a CAPTCHA exemption;
- authorised browser-automation terms.

This is a finding about **public documentation**, not proof that no non-public government integration exists. CAPTCHA presence is also not itself a published ban on browser automation; equally, absence of a published ban is not authorisation.

## Unknowns that require the resort’s authorised account

Run a controlled portal/app observation with a real authorised operator and a genuine filing:

1. capture every current arrival and departure field, mandatory marker and validation rule;
2. record CAPTCHA frequency, session lifetime, timeout/re-authentication, password-expiry and concurrent-login behaviour;
3. record save-draft, duplicate, correction, retry and portal-outage behaviour;
4. identify the authoritative success response, filed-history view, downloadable record and stable identifiers;
5. verify whether Form III exists in Su-Swagatam for accommodation keepers and whether it removes the web CAPTCHA dependency;
6. inspect notices/orders visible after login; and
7. ask the jurisdictional FRO/Bureau of Immigration in writing whether it offers or permits an API, bulk/PMS integration, service account, allowlisting, or unattended browser automation.

Do not submit synthetic foreigner data or probe hidden endpoints.

## Feasibility conclusion for version 1

- **Unattended data preparation:** feasible.
- **Unattended submission through a documented official API:** not presently evidenced.
- **Unattended browser submission:** technically unproven and operationally blocked by CAPTCHA whenever a fresh login is required; it must not rely on CAPTCHA solving or bypass.
- **Unattended mobile-app submission:** authorised in the Rules in principle, but implementation for accommodation keepers is unverified.
- **Release decision:** mandatory unattended filing remains a hard **go/no-go gate**. Proceed only if authorised observation proves a stable no-human session path, the official app supports keeper filing unattended, or the authority grants an integration/automation route in writing. Otherwise fully unattended version 1 is infeasible under the accepted constraints, and the product must not claim successful filing.
