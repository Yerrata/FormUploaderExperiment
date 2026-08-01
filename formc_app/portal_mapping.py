from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MappingStatus(StrEnum):
    DIRECT = "DIRECT"
    TRANSFORMED = "TRANSFORMED"
    DERIVED_UNCONFIRMED = "DERIVED_UNCONFIRMED"
    DERIVED = "DERIVED"
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
        "sex",
        ("applicant_sex",),
        MappingStatus.TRANSFORMED,
        "Select the exact portal code from SEX_CHOICE_CODES.",
    ),
    CandidatePortalMapping(
        "nationality",
        ("applicant_nationality",),
        MappingStatus.TRANSFORMED,
        "Select the portal ISO 3166-1 alpha-3 option matching the nationality.",
    ),
    CandidatePortalMapping(
        "permanent_address",
        ("applicant_permaddr",),
        MappingStatus.DIRECT,
        "Fill the guest-confirmed permanent address.",
    ),
    CandidatePortalMapping(
        "permanent_city",
        ("applicant_permcity",),
        MappingStatus.DIRECT,
        "Fill the guest-confirmed permanent city.",
    ),
    CandidatePortalMapping(
        "permanent_country",
        ("applicant_permcountry",),
        MappingStatus.TRANSFORMED,
        "Select the portal country option by exact normalized label.",
    ),
    CandidatePortalMapping(
        "passport_number",
        ("applicant_passpno",),
        MappingStatus.DIRECT,
        "Fill the validated passport number.",
    ),
    CandidatePortalMapping(
        "passport_place_of_issue",
        ("applicant_passplcofissue",),
        MappingStatus.DIRECT,
        "Fill the guest-confirmed passport place of issue.",
    ),
    CandidatePortalMapping(
        "passport_issue_country",
        ("passport_issue_country",),
        MappingStatus.TRANSFORMED,
        "Select the portal ISO 3166-1 alpha-3 option matching the issue country.",
    ),
    CandidatePortalMapping(
        "passport_date_of_issue",
        ("applicant_passpdoissue",),
        MappingStatus.TRANSFORMED,
        "Format the validated date as DD/MM/YYYY.",
    ),
    CandidatePortalMapping(
        "passport_valid_until",
        ("applicant_passpvalidtill",),
        MappingStatus.TRANSFORMED,
        "Format the validated date as DD/MM/YYYY.",
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
        "visa_place_of_issue",
        ("applicant_visaplcoissue",),
        MappingStatus.DIRECT,
        "Fill the guest-confirmed visa place of issue.",
    ),
    CandidatePortalMapping(
        "visa_issue_country",
        ("visa_issue_country",),
        MappingStatus.TRANSFORMED,
        "Select the portal ISO 3166-1 alpha-3 option matching the issue country.",
    ),
    CandidatePortalMapping(
        "visa_date_of_issue",
        ("applicant_visadoissue",),
        MappingStatus.TRANSFORMED,
        "Format the validated date as DD/MM/YYYY.",
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
        "arrived_from_country",
        ("applicant_arrivedfromcountry",),
        MappingStatus.TRANSFORMED,
        "Select the portal country option by exact normalized label.",
    ),
    CandidatePortalMapping(
        "arrived_from_city",
        ("applicant_arrivedfromcity",),
        MappingStatus.DIRECT,
        "Fill the guest-confirmed city.",
    ),
    CandidatePortalMapping(
        "arrived_from_place",
        ("applicant_arrivedfromplace",),
        MappingStatus.DIRECT,
        "Fill the guest-confirmed airport, port or place.",
    ),
    CandidatePortalMapping(
        "arrival_date_india",
        ("applicant_doarrivalindia",),
        MappingStatus.TRANSFORMED,
        "Format the guest-confirmed date as DD/MM/YYYY.",
    ),
    CandidatePortalMapping(
        "arrival_time_hotel",
        ("applicant_timeoarrivalhotel",),
        MappingStatus.TRANSFORMED,
        "Format the staff-supplied time as HH:MM; filling remains disabled until live acceptance is verified.",
    ),
    CandidatePortalMapping(
        "employed_in_india",
        ("employed",),
        MappingStatus.TRANSFORMED,
        "Select the exact radio code from EMPLOYMENT_CHOICE_CODES.",
    ),
    CandidatePortalMapping(
        "purpose_of_visit",
        ("applicant_purpovisit",),
        MappingStatus.TRANSFORMED,
        "Select the exact portal code from PURPOSE_OF_VISIT_CHOICE_CODES.",
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
        MappingStatus.DERIVED,
        "Derive the positive number of days between the validated check-in and checkout dates.",
    ),
    CandidatePortalMapping(
        "check_in_date",
        ("applicant_doarrivalhotel",),
        MappingStatus.TRANSFORMED,
        "Format the arrival-at-hotel date as DD/MM/YYYY.",
    ),
    CandidatePortalMapping(
        "special_category",
        (),
        MappingStatus.UNCONFIRMED,
        "Require and map this field only when its portal branch is explicitly activated.",
    ),
    CandidatePortalMapping(
        "visa_subtype",
        (),
        MappingStatus.UNCONFIRMED,
        "Require and map this field only when the selected visa type activates its portal branch.",
    ),
    CandidatePortalMapping(
        "room",
        (),
        MappingStatus.NOT_SUBMITTED,
        "Keep as Yeratta case metadata; no matching live Form C control was observed.",
    ),
    CandidatePortalMapping(
        "form_b_reference",
        (),
        MappingStatus.NOT_SUBMITTED,
        "Legacy optional metadata only; the MVP does not collect or submit it.",
    ),
)


LIVE_SUBMISSION_CONTROL_IDS = frozenset({"tmpsbmt", "pmsbmt"})
EMPLOYMENT_CHOICE_CODES = {"yes": "Y", "no": "N"}
SEX_CHOICE_CODES = {"male": "M", "female": "F", "transgender": "X"}
PURPOSE_OF_VISIT_CHOICE_CODES = {
    "accompanying_parents": "18",
    "accompanying_patient": "9",
    "accompanying_patient_as_doctor": "10",
    "accompanying_spouse": "17",
    "business": "6",
    "diplomatic": "12",
    "education": "5",
    "employment": "13",
    "internship": "19",
    "joining_spouse": "2",
    "journalism": "7",
    "medical_treatment_self": "8",
    "meeting_friends_relatives": "1",
    "minor_child_indian_parent": "3",
    "official": "11",
    "others": "15",
    "seminar_conference": "4",
    "studies": "14",
    "surrogacy": "20",
    "tourism": "16",
}
NEXT_DESTINATION_SCOPE_CODES = {"india": "I", "outside_india": "O"}
PROPERTY_CONFIG_PORTAL_CONTROLS = {
    "reference_address": "applicant_refaddr",
    "reference_state_code": "applicant_refstate",
    "reference_district_code": "applicant_refstatedistr",
    "reference_pin_code": "applicant_refpincode",
}


def mapping_by_candidate_field() -> dict[str, CandidatePortalMapping]:
    return {mapping.candidate_field: mapping for mapping in CANDIDATE_PORTAL_MAPPINGS}
