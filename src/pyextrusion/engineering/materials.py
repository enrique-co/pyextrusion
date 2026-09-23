from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .._strict import require_number, require_string
from .metadata import Interval, SourceRef

UNIVERSAL_GAS_CONSTANT_J_MOL_K = 8.314


def _validated_provenance(items: tuple[SourceRef, ...]) -> tuple[SourceRef, ...]:
    provenance = tuple(items)
    if any(not isinstance(item, SourceRef) for item in provenance):
        raise ValueError("material provenance entries must be SourceRef instances")
    return provenance


def _validated_notes(items: tuple[str, ...]) -> tuple[str, ...]:
    notes = tuple(items)
    for item in notes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("material notes entries must be non-empty strings")
    return notes


@dataclass(frozen=True)
class HotWorkingConstitutiveModel:
    """Constitutive constants for hot-deformation flow-stress calculations.

    The model stores only experimentally established constitutive parameters and
    their traceability. It does not infer chemistry corrections, homogenization
    effects, surrogate-alloy equivalence or a valid process window.

    alpha_mpa_inv is the reciprocal-stress coefficient used in the
    hyperbolic-sine law, n is the stress exponent, activation_energy_j_mol
    is the hot-deformation activation energy, and ln_A is the natural
    logarithm of the pre-exponential factor A in s^-1.

    Optional temperature and strain-rate ranges are absolute documented bounds.
    None means that PyExtrusion has no documented bound for that field; it does
    not imply unlimited validity.
    """

    alloy: str
    alpha_mpa_inv: float
    n: float
    activation_energy_j_mol: float
    ln_A: float
    gas_constant_j_mol_k: float = UNIVERSAL_GAS_CONSTANT_J_MOL_K
    temperature_range_c: Interval | None = None
    mean_strain_rate_range_s_1: Interval | None = None
    provenance: tuple[SourceRef, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        alloy = require_string(self.alloy, "alloy", ValueError).strip()
        alpha = require_number(
            self.alpha_mpa_inv,
            "alpha_mpa_inv",
            ValueError,
            minimum=0.0,
            exclusive_minimum=True,
        )
        exponent = require_number(self.n, "n", ValueError, minimum=0.0, exclusive_minimum=True)
        activation_energy = require_number(
            self.activation_energy_j_mol,
            "activation_energy_j_mol",
            ValueError,
            minimum=0.0,
            exclusive_minimum=True,
        )
        ln_a = require_number(self.ln_A, "ln_A", ValueError)
        gas_constant = require_number(
            self.gas_constant_j_mol_k,
            "gas_constant_j_mol_k",
            ValueError,
            minimum=0.0,
            exclusive_minimum=True,
        )
        assert (
            alpha is not None
            and exponent is not None
            and activation_energy is not None
            and ln_a is not None
            and gas_constant is not None
        )

        if self.temperature_range_c is not None and not isinstance(self.temperature_range_c, Interval):
            raise ValueError("temperature_range_c must be an Interval when provided")
        if self.mean_strain_rate_range_s_1 is not None and not isinstance(
            self.mean_strain_rate_range_s_1, Interval
        ):
            raise ValueError("mean_strain_rate_range_s_1 must be an Interval when provided")

        object.__setattr__(self, "alloy", alloy)
        object.__setattr__(self, "alpha_mpa_inv", alpha)
        object.__setattr__(self, "n", exponent)
        object.__setattr__(self, "activation_energy_j_mol", activation_energy)
        object.__setattr__(self, "ln_A", ln_a)
        object.__setattr__(self, "gas_constant_j_mol_k", gas_constant)
        object.__setattr__(self, "provenance", _validated_provenance(self.provenance))
        object.__setattr__(self, "notes", _validated_notes(self.notes))

    @property
    def A_s_1(self) -> float:
        """Return the pre-exponential factor A in s^-1."""
        try:
            value = math.exp(self.ln_A)
        except OverflowError as exc:
            raise ValueError("A_s_1 is outside the representable finite range") from exc
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("A_s_1 is outside the representable finite range")
        return value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SHEPPARD_1999_TABLE_4_1_AA6063 = SourceRef(
    source_kind="literature",
    reference="T. Sheppard, Extrusion of Aluminium Alloys (1999), Table 4.1",
    detail="AA6063 hot-working constitutive constants",
)

AA6063_SHEPPARD_1999 = HotWorkingConstitutiveModel(
    alloy="AA6063",
    alpha_mpa_inv=0.040,
    n=5.385,
    activation_energy_j_mol=141_550.0,
    ln_A=22.5,
    provenance=(SHEPPARD_1999_TABLE_4_1_AA6063,),
    notes=(
        "Constants are the AA6063 values tabulated by Sheppard.",
        "No automatic substitution for AA6060 or any other alloy is implied.",
    ),
)
