from __future__ import annotations

from formc_app.models import CandidateField


DUMMY_PROFILES: dict[str, dict[str, tuple[str | None, str]]] = {
    "daniel": {
        "surname": ("KOH", "passport_dummy"),
        "given_name": ("DANIEL", "passport_dummy"),
        "nationality": ("SINGAPORE", "passport_dummy"),
        "passport_number": ("E12345884", "passport_dummy"),
        "date_of_birth": ("1990-02-17", "passport_dummy"),
        "visa_number": ("E-VISA-772", "visa_dummy"),
        "visa_type": ("e-Tourist", "visa_dummy"),
        "visa_valid_until": ("2026-09-06", "visa_dummy"),
        "arrived_from": (None, "staff"),
        "next_destination": (None, "staff"),
    },
    "elena": {
        "surname": ("MARKOVIC", "passport_dummy"),
        "given_name": ("ELENA", "passport_dummy"),
        "nationality": ("CROATIA", "passport_dummy"),
        "passport_number": ("P77884491", "passport_dummy"),
        "date_of_birth": ("1987-11-03", "passport_dummy"),
        "visa_number": ("VISA-208", "visa_dummy"),
        "visa_type": ("e-Tourist", "visa_dummy"),
        "visa_valid_until": ("2026-10-19", "visa_dummy"),
        "arrived_from": ("Chennai", "staff"),
        "next_destination": (None, "staff"),
    },
    "aiko": {
        "surname": ("TANAKA", "passport_dummy"),
        "given_name": ("AIKO", "passport_dummy"),
        "nationality": ("JAPAN", "passport_dummy"),
        "passport_number": ("TR99001144", "passport_dummy"),
        "date_of_birth": ("1994-06-22", "passport_dummy"),
        "visa_number": ("JP-VISA-533", "visa_dummy"),
        "visa_type": ("e-Tourist", "visa_dummy"),
        "visa_valid_until": ("2026-11-21", "visa_dummy"),
        "arrived_from": ("Delhi", "staff"),
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
