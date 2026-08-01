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
| `check_out_date` | `applicant_intnddurhotel` | Derived | Positive calendar-day difference from the validated check-in date |
| `check_in_date` | `applicant_doarrivalhotel` | Transform | Format `DD/MM/YYYY` |
| `room` | none | Not submitted | Yeratta case metadata only |
| `form_b_reference` | possibly `Filerfno` | Unconfirmed | Never assume these references have the same meaning |

The executable contract is `formc_app/portal_mapping.py`. Every current Candidate field appears exactly once.

## Remaining required information absent from the Candidate

These live controls are marked with `*` by the government page but are not represented safely by the current Candidate:

- special category, whose captured options contain only special cases and no safe normal default;
- structured next destination, including its India/outside-India dependent controls;
- visa subtype when the chosen visa type makes that conditional control applicable;

The safe live catalogue confirms these closed choice codes:

- sex: `M`, `F` or `X`;
- employed in India: `Y` for yes, `N` for no;
- next destination: `I` for India, `O` for outside India.

The 20 purpose-of-visit choices are also frozen as semantic Candidate values mapped to exact portal codes. Unknown choice values are rejected rather than coerced.

Visa subtype is portal-dependent and must be handled only when the chosen visa type makes its options available.

## Property configuration rather than guest questions

The India reference address, state, district and PIN code come from one locked `data/property.json` on the Filing Worker. Guests do not type or alter the resort's own address. The application has no route that writes this configuration, and no real Yeratta values are committed to GitHub.

The final 55-control catalogue freezes these exact mappings:

| Property configuration field | Government control | Fill-plan rule |
|---|---|---|
| `reference_address` | `applicant_refaddr` | Fill locked text |
| `reference_state_code` | `applicant_refstate` | Select the exact configured code after confirming it exists in the static catalogue |
| `reference_district_code` | `applicant_refstatedistr` | State-dependent select; wait for its options, then require the exact configured code before selecting |
| `reference_pin_code` | `applicant_refpincode` | Fill the validated six-digit PIN |

The district catalogue is empty until a state is selected. The offline plan therefore marks that one operation `runtime_option_check_required`; a future executor must stop if the configured district code does not appear after selecting the state.

## Guest photograph and stay duration

The Ministry of Home Affairs' published [Form C](https://www.mha.gov.in/PDF_Other/AnnexIII_01022018.pdf#page=46) defines intended duration as a number of days and requires a photograph. It permits the passport photograph only when a web or digital camera is unavailable. The official [e-FRRO photo requirements](https://indianfrro.gov.in/) require JPEG and a maximum size of 1 MB, with a front view, open eyes and the full head centred in frame.

For this camera-equipped MVP:

- the Guest Session requires a separate, current guest-camera photograph;
- the guest confirms that it is front-facing, clear, eyes open and shows the complete head;
- the server decodes the image, rejects images below 240 pixels on either edge or above 25 megapixels, fixes EXIF orientation, converts it to JPEG, removes source metadata, limits its longest edge to 1,200 pixels and reduces it below the portal's 1 MB limit;
- the immutable Filing Request records the photo hash, approved source and suitability-confirmation time;
- preflight re-hashes the persisted photograph and refuses to plan the upload if it changed;
- `check_out_date - check_in_date` must be at least one day and is written to `applicant_intnddurhotel` as the positive number of days.

## Optional or operational controls

- Indian and permanent-country phone/mobile numbers and remarks are not marked mandatory in the captured page.
- A passport-page image is never silently reused as the guest photograph.
- Read-only age fields are portal-computed and must not be filled.
- `Filerfno`, `GetFileno` and adjacent buttons are operational controls whose meaning remains unconfirmed.

## Submission boundary

`tmpsbmt` and `pmsbmt` are live submission-related controls. The adapter must not click either during mapping or fill-only development. Human-reviewed submission remains disabled until the filled live page has been manually checked and a separate explicit release gate is approved.

## Deterministic offline preflight

`formc_app/fill_plan.py` compiles a sealed Candidate, locked property configuration and redacted portal catalogue into an atomic per-case `fill-plan.json`. It does not launch or interact with a browser and cannot fill or submit a form.

The compiler:

- verifies Candidate confirmation, readiness and the Filing Request hash;
- verifies the sealed guest-photo hash and prepares the exact `file1` upload without opening a browser;
- derives the government stay duration as a positive number of days;
- formats confirmed dates and frozen choice codes deterministically;
- resolves country and visa-type options only by one exact normalized catalogue label;
- rejects missing, duplicate, disabled, read-only or structurally changed controls and static options;
- requires an exact runtime option check for the state-dependent property district select;
- excludes room metadata and both live submission controls;
- keeps live filling and live submission explicitly disabled;
- reports every unresolved semantic item above as a blocker rather than guessing.

## Structural probe status

Complete. The final catalogue captured all 55 controls and the four safe radio choice codes. Values from text, file, hidden, password and button inputs remain excluded.
