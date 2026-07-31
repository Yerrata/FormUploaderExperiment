from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


PROPERTY_CONFIG_FILENAME = "property.json"


class PropertyConfigError(RuntimeError):
    pass


class YerattaPropertyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_address: str
    reference_state_code: str
    reference_district_code: str
    reference_pin_code: str

    @field_validator("*")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Property configuration values cannot be empty")
        return trimmed

    @field_validator("reference_pin_code")
    @classmethod
    def require_six_digit_pin(cls, value: str) -> str:
        if len(value) != 6 or not value.isdigit():
            raise ValueError("Property PIN code must contain exactly six digits")
        return value


def load_property_config(data_root: Path) -> YerattaPropertyConfig:
    path = data_root / PROPERTY_CONFIG_FILENAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return YerattaPropertyConfig.model_validate(payload)
    except FileNotFoundError as exc:
        raise PropertyConfigError(
            f"Missing locked Filing Worker property configuration: {path}"
        ) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise PropertyConfigError(f"Invalid property configuration: {path}") from exc
