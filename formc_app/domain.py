from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FormField:
    name: str
    label: str
    question: str | None = None
    critical: bool = False
    input_type: str = "text"
    choices: tuple[tuple[str, str], ...] = ()


SEX_CHOICES = (
    ("male", "Male"),
    ("female", "Female"),
    ("transgender", "Transgender"),
)

EMPLOYMENT_CHOICES = (("yes", "Yes"), ("no", "No"))

PURPOSE_OF_VISIT_CHOICES = (
    ("accompanying_parents", "Accompanying parents"),
    ("accompanying_patient", "Accompanying patient"),
    ("accompanying_patient_as_doctor", "Accompanying patient as doctor"),
    ("accompanying_spouse", "Accompanying spouse"),
    ("business", "Business"),
    ("diplomatic", "Diplomatic"),
    ("education", "Education"),
    ("employment", "Employment"),
    ("internship", "Internship"),
    ("joining_spouse", "Joining spouse"),
    ("journalism", "Journalism"),
    ("medical_treatment_self", "Medical treatment of self"),
    ("meeting_friends_relatives", "Meeting friends or relatives"),
    ("minor_child_indian_parent", "Minor child with an Indian parent"),
    ("official", "Official"),
    ("others", "Others"),
    ("seminar_conference", "Seminar or conference in India"),
    ("studies", "Studies"),
    ("surrogacy", "Surrogacy"),
    ("tourism", "Tourism"),
)


FORM_FIELDS = (
    FormField("surname", "Surname", critical=True),
    FormField("given_name", "Given name", critical=True),
    FormField(
        "sex",
        "Sex",
        critical=True,
        input_type="select",
        choices=SEX_CHOICES,
    ),
    FormField("nationality", "Nationality", critical=True),
    FormField(
        "permanent_address",
        "Permanent address",
        "What is your address in the country where you permanently reside?",
    ),
    FormField(
        "permanent_city",
        "Permanent city",
        "Which city is that permanent address in?",
    ),
    FormField(
        "permanent_country",
        "Permanent country",
        "Which country do you permanently reside in?",
    ),
    FormField("passport_number", "Passport number", critical=True),
    FormField("date_of_birth", "Date of birth", critical=True, input_type="date"),
    FormField("passport_place_of_issue", "Passport place of issue", critical=True),
    FormField("passport_issue_country", "Passport issue country", critical=True),
    FormField(
        "passport_date_of_issue",
        "Passport date of issue",
        critical=True,
        input_type="date",
    ),
    FormField(
        "passport_valid_until",
        "Passport valid until",
        critical=True,
        input_type="date",
    ),
    FormField("visa_number", "Visa number", critical=True),
    FormField("visa_place_of_issue", "Visa place of issue", critical=True),
    FormField("visa_issue_country", "Visa issue country", critical=True),
    FormField(
        "visa_date_of_issue",
        "Visa date of issue",
        critical=True,
        input_type="date",
    ),
    FormField("visa_type", "Visa type", critical=True),
    FormField(
        "visa_valid_until",
        "Visa valid until",
        critical=True,
        input_type="date",
    ),
    FormField(
        "arrived_from_country",
        "Arrived from country",
        "Which country did you arrive from immediately before this stay?",
    ),
    FormField(
        "arrived_from_city",
        "Arrived from city",
        "Which city did you arrive from immediately before this stay?",
    ),
    FormField(
        "arrived_from_place",
        "Arrived from place",
        "Which airport, port or place did you arrive from immediately before this stay?",
    ),
    FormField(
        "arrival_date_india",
        "Date of arrival in India",
        "On which date did you arrive in India on this trip?",
        input_type="date",
    ),
    FormField(
        "arrival_time_hotel",
        "Time of arrival at Yeratta",
        "At what time did you arrive at Yeratta?",
        input_type="time",
    ),
    FormField(
        "employed_in_india",
        "Employed in India",
        "Are you employed in India?",
        input_type="select",
        choices=EMPLOYMENT_CHOICES,
    ),
    FormField(
        "purpose_of_visit",
        "Purpose of visit",
        "What is the purpose of your visit to India?",
        input_type="select",
        choices=PURPOSE_OF_VISIT_CHOICES,
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
        input_type="date",
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


def intended_stay_days(check_in_value: str, check_out_value: str) -> int:
    """Return the positive Form C stay duration for two ISO calendar dates."""
    try:
        check_in = date.fromisoformat(check_in_value)
        check_out = date.fromisoformat(check_out_value)
    except ValueError as exc:
        raise ValueError("Check-in and checkout must be valid ISO dates") from exc
    duration = (check_out - check_in).days
    if duration < 1:
        raise ValueError("Checkout must be later than check-in")
    return duration
