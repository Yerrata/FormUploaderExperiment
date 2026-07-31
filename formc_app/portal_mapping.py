from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MappingStatus(StrEnum):
    DIRECT = "DIRECT"
    TRANSFORMED = "TRANSFORMED"
    DERIVED_UNCONFIRMED = "DERIVED_UNCONFIRMED"
    SCHEMA_CHANGE_REQUIRED = "SCHEMA_CHANGE_REQUIRED"
    NOT_SUBMITTED = "NOT_SUBMITTED"
    UNCONFIRMED = "UNCONFIRMED"


@dataclass(frozen=True)
class CandidatePortalMapping:
    candidate_field: str
    portal_controls: tuple[str, ...]
    status: MappingStatus
    rule: str


CANDIDATE_PORTAL_MAPPINGS = (
    CandidatePortalMapping(
        "surname",
        ("applicant_surname",),
        MappingStatus.DIRECT,
        "Fill text unchanged after normal Candidate validation.",
    ),
    CandidatePortalMapping(
        "given_name",
        ("applicant_givenname",),
        MappingStatus.DIRECT,
        "Fill text unchanged after normal Candidate validation.",
    ),
    CandidatePortalMapping(
        "nationality",
        ("applicant_nationality",),
        MappingStatus.TRANSFORMED,
        "Select the portal ISO 3166-1 alpha-3 option matching the nationality.",
    ),
    CandidatePortalMapping(
        "passport_number",
        ("applicant_passpno",),
        MappingStatus.DIRECT,
        "Fill the validated passport number.",
    ),
    CandidatePortalMapping(
        "date_of_birth",
        ("dobformat", "applicant_dob"),
        MappingStatus.TRANSFORMED,
        "Select DY and format a complete birth date as DD/MM/YYYY.",
    ),
    CandidatePortalMapping(
        "visa_number",
        ("applicant_visano",),
        MappingStatus.DIRECT,
        "Fill the validated visa number.",
    ),
    CandidatePortalMapping(
        "visa_type",
        ("applicant_visatype",),
        MappingStatus.TRANSFORMED,
        "Select the exact closed portal visa-type option; never guess a near match.",
    ),
    CandidatePortalMapping(
        "visa_valid_until",
        ("applicant_visavalidtill",),
        MappingStatus.TRANSFORMED,
        "Format the validated date as DD/MM/YYYY.",
    ),
    CandidatePortalMapping(
        "arrived_from",
        (
            "applicant_arrivedfromcountry",
            "applicant_arrivedfromcity",
            "applicant_arrivedfromplace",
        ),
        MappingStatus.SCHEMA_CHANGE_REQUIRED,
        "Replace the single free-text field with country, city and place fields.",
    ),
    CandidatePortalMapping(
        "next_destination",
        (
            "applicant_next_dest_country_flag_r",
            "applicant_next_destination_state_IN",
            "applicant_next_destination_city_district_IN",
            "applicant_next_destination_place_IN",
        ),
        MappingStatus.SCHEMA_CHANGE_REQUIRED,
        "Replace free text with destination country branch plus structured location.",
    ),
    CandidatePortalMapping(
        "check_out_date",
        ("applicant_intnddurhotel",),
        MappingStatus.DERIVED_UNCONFIRMED,
        "Derive intended stay duration with check-in date only after portal units are confirmed.",
    ),
    CandidatePortalMapping(
        "check_in_date",
        ("applicant_doarrivalhotel",),
        MappingStatus.TRANSFORMED,
        "Format the arrival-at-hotel date as DD/MM/YYYY.",
    ),
    CandidatePortalMapping(
        "room",
        (),
        MappingStatus.NOT_SUBMITTED,
        "Keep as Yeratta case metadata; no matching live Form C control was observed.",
    ),
    CandidatePortalMapping(
        "form_b_reference",
        ("Filerfno",),
        MappingStatus.UNCONFIRMED,
        "Do not assume the portal filer reference is the physical Form B reference.",
    ),
)


LIVE_SUBMISSION_CONTROL_IDS = frozenset({"tmpsbmt", "pmsbmt"})


def mapping_by_candidate_field() -> dict[str, CandidatePortalMapping]:
    return {mapping.candidate_field: mapping for mapping in CANDIDATE_PORTAL_MAPPINGS}
