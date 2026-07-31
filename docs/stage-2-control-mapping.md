# Stage 2 live Form C control mapping

Source: the read-only catalogue captured on the Yeratta Filing Worker on 31 July 2026. It found 55 safe controls. No current field values, credentials, CAPTCHA data, cookies, signed URLs, HTML or screenshots were captured.

## Existing Candidate Form C mapping

| Candidate field | Government control | Status | Rule |
|---|---|---|---|
| `surname` | `applicant_surname` | Direct | Validated text |
| `given_name` | `applicant_givenname` | Direct | Validated text |
| `sex` | `applicant_sex` | Transform | Exact `M`, `F` or `X` code from a closed Candidate choice |
| `nationality` | `applicant_nationality` | Transform | Select matching ISO alpha-3 option |
| `permanent_address` | `applicant_permaddr` | Direct | Guest-confirmed text |
| `permanent_city` | `applicant_permcity` | Direct | Guest-confirmed text |
| `permanent_country` | `applicant_permcountry` | Transform | Exact normalized country-option match |
| `passport_number` | `applicant_passpno` | Direct | Validated text |
| `date_of_birth` | `dobformat`, `applicant_dob` | Transform | Select `DY`; format `DD/MM/YYYY` |
| `passport_place_of_issue` | `applicant_passplcofissue` | Direct | Guest-confirmed text |
| `passport_issue_country` | `passport_issue_country` | Transform | Select matching ISO alpha-3 option |
| `passport_date_of_issue` | `applicant_passpdoissue` | Transform | Format `DD/MM/YYYY` |
| `passport_valid_until` | `applicant_passpvalidtill` | Transform | Format `DD/MM/YYYY` |
| `visa_number` | `applicant_visano` | Direct | Validated text |
| `visa_place_of_issue` | `applicant_visaplcoissue` | Direct | Guest-confirmed text |
| `visa_issue_country` | `visa_issue_country` | Transform | Select matching ISO alpha-3 option |
| `visa_date_of_issue` | `applicant_visadoissue` | Transform | Format `DD/MM/YYYY` |
| `visa_type` | `applicant_visatype` | Transform | Exact closed-option match; never fuzzy-match |
| `visa_valid_until` | `applicant_visavalidtill` | Transform | Format `DD/MM/YYYY` |
| `arrived_from_country` | `applicant_arrivedfromcountry` | Transform | Exact normalized country-option match |
| `arrived_from_city` | `applicant_arrivedfromcity` | Direct | Guest-confirmed text |
| `arrived_from_place` | `applicant_arrivedfromplace` | Direct | Guest-confirmed text |
| `arrival_date_india` | `applicant_doarrivalindia` | Transform | Format `DD/MM/YYYY` |
| `arrival_time_hotel` | `applicant_timeoarrivalhotel` | Transform | Format `HH:MM`; verify live acceptance before filling |
| `employed_in_india` | radio `employed` | Transform | Exact `Y` or `N` code from a closed Candidate choice |
| `purpose_of_visit` | `applicant_purpovisit` | Transform | Exact code from the frozen 20-option catalogue |
| `next_destination` | destination branch, state/city/place controls | Schema change | Replace free text with the portal's structured branch |
| `check_out_date` | `applicant_intnddurhotel` | Unconfirmed derivation | Confirm whether the portal expects days or nights before deriving |
| `check_in_date` | `applicant_doarrivalhotel` | Transform | Format `DD/MM/YYYY` |
| `room` | none | Not submitted | Yeratta case metadata only |
| `form_b_reference` | possibly `Filerfno` | Unconfirmed | Never assume these references have the same meaning |

The executable contract is `formc_app/portal_mapping.py`. Every current Candidate field appears exactly once.

## Remaining required information absent from the Candidate

These live controls are marked with `*` by the government page but are not represented safely by the current Candidate:

- special category, whose captured options contain only special cases and no safe normal default;
- structured next destination, including its India/outside-India dependent controls;
- visa subtype when the chosen visa type makes that conditional control applicable;
- a policy-approved source for the required guest photograph.

The safe live catalogue confirms these closed choice codes:

- sex: `M`, `F` or `X`;
- employed in India: `Y` for yes, `N` for no;
- next destination: `I` for India, `O` for outside India.

The 20 purpose-of-visit choices are also frozen as semantic Candidate values mapped to exact portal codes. Unknown choice values are rejected rather than coerced.

Visa subtype is portal-dependent and must be handled only when the chosen visa type makes its options available.

## Property configuration rather than guest questions

The India reference address, state, district and PIN code come from one locked `data/property.json` on the Filing Worker. Guests do not type or alter the resort's own address. The application has no route that writes this configuration, and no real Yeratta values are committed to GitHub.

## Optional or operational controls

- Indian and permanent-country phone/mobile numbers and remarks are not marked mandatory in the captured page.
- Guest photo upload needs an explicit source and suitability rule; a passport-page photograph must not silently be treated as the required guest photo.
- Read-only age fields are portal-computed and must not be filled.
- `Filerfno`, `GetFileno` and adjacent buttons are operational controls whose meaning remains unconfirmed.

## Submission boundary

`tmpsbmt` and `pmsbmt` are live submission-related controls. The adapter must not click either during mapping or fill-only development. Human-reviewed submission remains disabled until the filled live page has been manually checked and a separate explicit release gate is approved.

## Structural probe status

Complete. The final catalogue captured all 55 controls and the four safe radio choice codes. Values from text, file, hidden, password and button inputs remain excluded.
