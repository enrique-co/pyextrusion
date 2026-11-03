"""Validation and serialization rules for explicit production-family requests."""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from ._strict import require_int
from .errors import InvalidProductionInputError, UnsupportedSchemaVersionError

ConfigurationName = Literal[
    "1_billet_1_profile", "k_billets_1_profile", "1_billet_2_profiles"
]
CONFIGURATION_NAMES = ("1_billet_1_profile", "k_billets_1_profile", "1_billet_2_profiles")
SELECTION_SCHEMA_VERSION = "1.2"


def validate_selection(configuration: object, billets_per_pull: object, *, prefix: str) -> None:
    if configuration is not None and (
        not isinstance(configuration, str) or configuration not in CONFIGURATION_NAMES
    ):
        raise InvalidProductionInputError(
            f"{prefix}.configuration must be null or one of: {', '.join(CONFIGURATION_NAMES)}"
        )
    if configuration == "k_billets_1_profile":
        require_int(billets_per_pull, f"{prefix}.billets_per_pull", InvalidProductionInputError, minimum=2)
    elif billets_per_pull is not None:
        raise InvalidProductionInputError(
            f"{prefix}.billets_per_pull requires configuration='k_billets_1_profile'"
        )


def input_dict(value) -> dict:
    data = asdict(value)
    # Preserve the pre-extension JSON shape of unforced cases.
    if data.get("configuration") is None:
        data.pop("configuration", None)
        data.pop("billets_per_pull", None)
    return data


def case_schema(schema_version: str | None, configuration: ConfigurationName | None) -> str:
    version = schema_version or (SELECTION_SCHEMA_VERSION if configuration is not None else "1.1")
    if configuration is not None and version != SELECTION_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError("Explicit production-family selection requires schema_version='1.2'")
    return version
