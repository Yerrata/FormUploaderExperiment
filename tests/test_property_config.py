import json
from pathlib import Path

import pytest

from formc_app.property_config import PropertyConfigError, load_property_config


def test_property_config_loads_only_from_the_filing_worker_data_folder(tmp_path: Path):
    (tmp_path / "property.json").write_text(
        json.dumps(
            {
                "reference_address": "Yeratta local test address",
                "reference_state_code": "35",
                "reference_district_code": "640",
                "reference_pin_code": "744211",
            }
        ),
        encoding="utf-8",
    )

    config = load_property_config(tmp_path)

    assert config.reference_address == "Yeratta local test address"
    assert config.reference_pin_code == "744211"


def test_missing_or_invalid_property_config_fails_closed(tmp_path: Path):
    with pytest.raises(PropertyConfigError, match="Missing locked"):
        load_property_config(tmp_path)

    (tmp_path / "property.json").write_text(
        '{"reference_address":"x","reference_state_code":"35",'
        '"reference_district_code":"640","reference_pin_code":"wrong"}',
        encoding="utf-8",
    )
    with pytest.raises(PropertyConfigError, match="Invalid property"):
        load_property_config(tmp_path)
