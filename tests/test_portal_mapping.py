from formc_app.domain import REQUIRED_FIELD_NAMES
from formc_app.portal_mapping import (
    CANDIDATE_PORTAL_MAPPINGS,
    EMPLOYMENT_CHOICE_CODES,
    LIVE_SUBMISSION_CONTROL_IDS,
    MappingStatus,
    NEXT_DESTINATION_SCOPE_CODES,
    mapping_by_candidate_field,
)


def test_every_current_candidate_field_has_one_explicit_mapping():
    mappings = mapping_by_candidate_field()

    assert set(mappings) == set(REQUIRED_FIELD_NAMES)
    assert len(mappings) == len(CANDIDATE_PORTAL_MAPPINGS)


def test_mapping_never_targets_a_live_submission_control():
    mapped_controls = {
        control
        for mapping in CANDIDATE_PORTAL_MAPPINGS
        for control in mapping.portal_controls
    }

    assert mapped_controls.isdisjoint(LIVE_SUBMISSION_CONTROL_IDS)


def test_ambiguous_candidate_fields_fail_closed():
    mappings = mapping_by_candidate_field()

    assert mappings["arrived_from"].status == MappingStatus.SCHEMA_CHANGE_REQUIRED
    assert mappings["next_destination"].status == MappingStatus.SCHEMA_CHANGE_REQUIRED
    assert mappings["check_out_date"].status == MappingStatus.DERIVED_UNCONFIRMED
    assert mappings["form_b_reference"].status == MappingStatus.UNCONFIRMED


def test_live_radio_choice_codes_are_frozen_from_the_safe_catalogue():
    assert EMPLOYMENT_CHOICE_CODES == {"yes": "Y", "no": "N"}
    assert NEXT_DESTINATION_SCOPE_CODES == {"india": "I", "outside_india": "O"}
