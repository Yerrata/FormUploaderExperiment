# Stage 2 live Form C control mapping

Source: the read-only catalogue captured on the Yeratta Filing Worker on 31 July 2026. It found 55 safe controls. No current field values, credentials, CAPTCHA data, cookies, signed URLs, HTML or screenshots were captured.

## Existing Candidate Form C mapping

| Candidate field | Government control | Status | Rule |
|---|---|---|---|
| `surname` | `applicant_surname` | Direct | Validated text |
| `given_name` | `applicant_givenname` | Direct | Validated text |
| `nationality` | `applicant_nationality` | Transform | Select matching ISO alpha-3 option |
| `passport_number` | `applicant_passpno` | Direct | Validated text |
| `date_of_birth` | `dobformat`, `applicant_dob` | Transform | Select `DY`; format `DD/MM/YYYY` |
| `visa_number` | `applicant_visano` | Direct | Validated text |
| `visa_type` | `applicant_visatype` | Transform | Exact closed-option match; never fuzzy-match |
| `visa_valid_until` | `applicant_visavalidtill` | Transform | Format `DD/MM/YYYY` |
| `arrived_from` | country, city and place controls | Schema change | Replace the ambiguous free-text field with three fields |
| `next_destination` | destination branch, state/city/place controls | Schema change | Replace free text with the portal's structured branch |
| `check_out_date` | `applicant_intnddurhotel` | Unconfirmed derivation | Confirm whether the portal expects days or nights before deriving |
| `check_in_date` | `applicant_doarrivalhotel` | Transform | Format `DD/MM/YYYY` |
| `room` | none | Not submitted | Yeratta case metadata only |
| `form_b_reference` | possibly `Filerfno` | Unconfirmed | Never assume these references have the same meaning |

The executable contract is `formc_app/portal_mapping.py`. Every current Candidate field appears exactly once.

## Required information absent from the Candidate

These live controls are marked with `*` by the government page but are not represented safely by the current Candidate:

- sex and special category;
- permanent residential address, city and country;
- passport place/country of issue, issue date and validity date;
- visa place/country of issue and issue date;
- structured arrival country, city and place;
- arrival date in India and arrival time at Yeratta;
- employment-in-India choice and purpose of visit;
- structured next destination.

Visa subtype is portal-dependent and must be handled only when the chosen visa type makes its options available.

## Property configuration rather than guest questions

The India reference address, state, district and PIN code should come from one locked Yeratta property configuration. Guests must not repeatedly type the resort's own address.

## Optional or operational controls

- Indian and permanent-country phone/mobile numbers and remarks are not marked mandatory in the captured page.
- Guest photo upload needs an explicit source and suitability rule; a passport-page photograph must not silently be treated as the required guest photo.
- Read-only age fields are portal-computed and must not be filled.
- `Filerfno`, `GetFileno` and adjacent buttons are operational controls whose meaning remains unconfirmed.

## Submission boundary

`tmpsbmt` and `pmsbmt` are live submission-related controls. The adapter must not click either during mapping or fill-only development. Human-reviewed submission remains disabled until the filled live page has been manually checked and a separate explicit release gate is approved.

## Remaining structural probe

The first catalogue deliberately excluded all input values. Radio-button values are static choice codes, not guest data, and are needed to distinguish the two employment and destination choices. The revised catalogue records a `choice_value` only for radio and checkbox controls while continuing to exclude values from text, file, hidden, password and button inputs.
