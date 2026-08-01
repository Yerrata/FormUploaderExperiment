from itertools import combinations

from formc_app.domain import (
    CONDITIONALLY_REQUIRED_FIELD_NAMES,
    EMPLOYMENT_CHOICES,
    FORM_FIELDS,
    GUEST_QUESTION_FIELD_NAMES,
    INTERNAL_HOTEL_METADATA_FIELD_NAMES,
    OPTIONAL_FIELD_NAMES,
    PURPOSE_OF_VISIT_CHOICES,
    REQUIRED_FORM_C_FIELD_NAMES,
    SEX_CHOICES,
    required_form_c_field_names,
)
from formc_app.portal_mapping import (
    CANDIDATE_PORTAL_MAPPINGS,
    EMPLOYMENT_CHOICE_CODES,
    LIVE_SUBMISSION_CONTROL_IDS,
    MappingStatus,
    NEXT_DESTINATION_SCOPE_CODES,
    PROPERTY_CONFIG_PORTAL_CONTROLS,
    PURPOSE_OF_VISIT_CHOICE_CODES,
    SEX_CHOICE_CODES,
    mapping_by_candidate_field,
)


def test_every_current_candidate_field_has_one_explicit_mapping():
    mappings = mapping_by_candidate_field()

    assert set(mappings) == {field.name for field in FORM_FIELDS}
    assert len(mappings) == len(CANDIDATE_PORTAL_MAPPINGS)


def test_fields_have_four_disjoint_readiness_categories():
    categories = (
        set(REQUIRED_FORM_C_FIELD_NAMES),
        set(CONDITIONALLY_REQUIRED_FIELD_NAMES),
        set(INTERNAL_HOTEL_METADATA_FIELD_NAMES),
        set(OPTIONAL_FIELD_NAMES),
    )

    assert set().union(*categories) == {field.name for field in FORM_FIELDS}
    assert all(not left & right for left, right in combinations(categories, 2))
    assert required_form_c_field_names() == REQUIRED_FORM_C_FIELD_NAMES
    assert required_form_c_field_names(("visa_subtype",)) == (
        *REQUIRED_FORM_C_FIELD_NAMES,
        "visa_subtype",
    )
    assert "arrival_time_hotel" not in GUEST_QUESTION_FIELD_NAMES
    assert "room" not in REQUIRED_FORM_C_FIELD_NAMES
    assert "form_b_reference" not in REQUIRED_FORM_C_FIELD_NAMES


def test_mapping_never_targets_a_live_submission_control():
    mapped_controls = {
        control
        for mapping in CANDIDATE_PORTAL_MAPPINGS
        for control in mapping.portal_controls
    }

    assert mapped_controls.isdisjoint(LIVE_SUBMISSION_CONTROL_IDS)


def test_ambiguous_candidate_fields_fail_closed():
    mappings = mapping_by_candidate_field()

    assert mappings["next_destination"].status == MappingStatus.SCHEMA_CHANGE_REQUIRED
    assert mappings["check_out_date"].status == MappingStatus.DERIVED
    assert mappings["special_category"].status == MappingStatus.UNCONFIRMED
    assert mappings["visa_subtype"].status == MappingStatus.UNCONFIRMED
    assert mappings["form_b_reference"].status == MappingStatus.NOT_SUBMITTED


def test_live_radio_choice_codes_are_frozen_from_the_safe_catalogue():
    assert EMPLOYMENT_CHOICE_CODES == {"yes": "Y", "no": "N"}
    assert SEX_CHOICE_CODES == {"male": "M", "female": "F", "transgender": "X"}
    assert NEXT_DESTINATION_SCOPE_CODES == {"india": "I", "outside_india": "O"}
    assert PURPOSE_OF_VISIT_CHOICE_CODES["tourism"] == "16"
    assert len(PURPOSE_OF_VISIT_CHOICE_CODES) == 20
    assert set(dict(SEX_CHOICES)) == set(SEX_CHOICE_CODES)
    assert set(dict(EMPLOYMENT_CHOICES)) == set(EMPLOYMENT_CHOICE_CODES)
    assert set(dict(PURPOSE_OF_VISIT_CHOICES)) == set(PURPOSE_OF_VISIT_CHOICE_CODES)


def test_property_control_identifiers_are_frozen_from_the_safe_catalogue():
    assert PROPERTY_CONFIG_PORTAL_CONTROLS == {
        "reference_address": "applicant_refaddr",
        "reference_state_code": "applicant_refstate",
        "reference_district_code": "applicant_refstatedistr",
        "reference_pin_code": "applicant_refpincode",
    }
