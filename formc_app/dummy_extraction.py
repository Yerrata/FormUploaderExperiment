from __future__ import annotations

from formc_app.models import CandidateField


DUMMY_PROFILES: dict[str, dict[str, tuple[str | None, str]]] = {
    "daniel": {
        "surname": ("KOH", "passport_dummy"),
        "given_name": ("DANIEL", "passport_dummy"),
        "sex": ("male", "passport_dummy"),
        "nationality": ("SINGAPORE", "passport_dummy"),
        "passport_number": ("E12345884", "passport_dummy"),
        "date_of_birth": ("1990-02-17", "passport_dummy"),
        "passport_place_of_issue": ("SINGAPORE", "passport_dummy"),
        "passport_issue_country": ("SINGAPORE", "passport_dummy"),
        "passport_date_of_issue": ("2021-09-07", "passport_dummy"),
        "passport_valid_until": ("2031-09-06", "passport_dummy"),
        "visa_number": ("E-VISA-772", "visa_dummy"),
        "visa_place_of_issue": ("SINGAPORE", "visa_dummy"),
        "visa_issue_country": ("SINGAPORE", "visa_dummy"),
        "visa_date_of_issue": ("2026-06-07", "visa_dummy"),
        "visa_type": ("e-Tourist", "visa_dummy"),
        "visa_valid_until": ("2026-09-06", "visa_dummy"),
        "next_destination": (None, "staff"),
    },
    "elena": {
        "surname": ("MARKOVIC", "passport_dummy"),
        "given_name": ("ELENA", "passport_dummy"),
        "sex": ("female", "passport_dummy"),
        "nationality": ("CROATIA", "passport_dummy"),
        "passport_number": ("P77884491", "passport_dummy"),
        "date_of_birth": ("1987-11-03", "passport_dummy"),
        "passport_place_of_issue": ("ZAGREB", "passport_dummy"),
        "passport_issue_country": ("CROATIA", "passport_dummy"),
        "passport_date_of_issue": ("2022-04-02", "passport_dummy"),
        "passport_valid_until": ("2032-04-01", "passport_dummy"),
        "visa_number": ("VISA-208", "visa_dummy"),
        "visa_place_of_issue": ("ZAGREB", "visa_dummy"),
        "visa_issue_country": ("CROATIA", "visa_dummy"),
        "visa_date_of_issue": ("2026-07-20", "visa_dummy"),
        "visa_type": ("e-Tourist", "visa_dummy"),
        "visa_valid_until": ("2026-10-19", "visa_dummy"),
        "next_destination": (None, "staff"),
    },
    "aiko": {
        "surname": ("TANAKA", "passport_dummy"),
        "given_name": ("AIKO", "passport_dummy"),
        "sex": ("female", "passport_dummy"),
        "nationality": ("JAPAN", "passport_dummy"),
        "passport_number": ("TR99001144", "passport_dummy"),
        "date_of_birth": ("1994-06-22", "passport_dummy"),
        "passport_place_of_issue": ("TOKYO", "passport_dummy"),
        "passport_issue_country": ("JAPAN", "passport_dummy"),
        "passport_date_of_issue": ("2023-01-13", "passport_dummy"),
        "passport_valid_until": ("2033-01-12", "passport_dummy"),
        "visa_number": ("JP-VISA-533", "visa_dummy"),
        "visa_place_of_issue": ("TOKYO", "visa_dummy"),
        "visa_issue_country": ("JAPAN", "visa_dummy"),
        "visa_date_of_issue": ("2026-08-22", "visa_dummy"),
        "visa_type": ("e-Tourist", "visa_dummy"),
        "visa_valid_until": ("2026-11-21", "visa_dummy"),
        "next_destination": ("Chennai", "staff"),
    },
}


def extract_dummy(profile: str) -> dict[str, CandidateField]:
    try:
        values = DUMMY_PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"Unknown dummy extraction profile: {profile}") from exc
    return {
        name: CandidateField(value=value, source=source)  # type: ignore[arg-type]
        for name, (value, source) in values.items()
    }
