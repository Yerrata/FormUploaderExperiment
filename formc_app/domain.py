from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormField:
    name: str
    label: str
    question: str | None = None
    critical: bool = False


FORM_FIELDS = (
    FormField("surname", "Surname", critical=True),
    FormField("given_name", "Given name", critical=True),
    FormField("nationality", "Nationality", critical=True),
    FormField("passport_number", "Passport number", critical=True),
    FormField("date_of_birth", "Date of birth", critical=True),
    FormField("visa_number", "Visa number", critical=True),
    FormField("visa_type", "Visa type", critical=True),
    FormField("visa_valid_until", "Visa valid until", critical=True),
    FormField(
        "arrived_from",
        "Arrived from",
        "Which city or port did you arrive from immediately before Havelock?",
    ),
    FormField(
        "next_destination",
        "Next destination",
        "Where will you travel immediately after leaving Yeratta Resort?",
    ),
    FormField(
        "check_out_date",
        "Expected checkout date",
        "On which date do you expect to check out?",
    ),
    FormField("check_in_date", "Check-in date"),
    FormField("room", "Room"),
    FormField("form_b_reference", "Physical Form B reference"),
)

FIELD_BY_NAME = {field.name: field for field in FORM_FIELDS}
REQUIRED_FIELD_NAMES = tuple(field.name for field in FORM_FIELDS)
EXTRACTED_FIELD_NAMES = tuple(
    field.name for field in FORM_FIELDS if field.critical
)
QUESTION_FIELD_NAMES = tuple(
    field.name for field in FORM_FIELDS if field.question is not None
)
