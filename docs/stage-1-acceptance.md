# Stage 1 acceptance checklist

Record the date, software commit, operator and evidence for every check. Stage 2 must not begin until all checks pass on the Yeratta phone/tablet and Filing Worker computer.

## Gate

- [ ] Complete five different dummy cases from a phone.
- [ ] Confirm every wizard answer reaches the corresponding mock Form C field.
- [ ] Correct at least one extracted field and confirm both the original and guest-corrected values remain in `candidate.json`.
- [ ] Confirm an absent mandatory answer blocks creation of the Filing Request.
- [ ] Confirm every completed case contains final JSON, pre-submit screenshot, evidence manifest and acknowledgement screenshot.
- [ ] Restart the application during the queue workflow and confirm no case is lost or processed twice.
- [ ] Confirm a guest link cannot view another case, staff pages or Filing Worker controls.
- [ ] Ask a staff operator unfamiliar with the code to identify every case's state and next action from Outstanding Cases.

## Hard failures

Do not accept Stage 1 if any test produces an incorrect field mapping, mutable post-confirmation guest data, duplicate submission, missing pre-submit evidence or false success status.
