"""Explicit legacy trim migration; never infer the physical production family."""
from dataclasses import replace

from .errors import InvalidProductionInputError
from .models import PlanningCase, StudyCase


def migrate_legacy_trim(
    case: StudyCase | PlanningCase, *, profiles_per_billet: int,
    use_multi_billet_override: bool | None = None,
) -> StudyCase | PlanningCase:
    """Convert a known legacy family to canonical total trim per incoming billet.

    Supply the verified legacy family (1 or 2 sequential pulls per billet).
    If a multi-billet override exists, explicitly choose whether it was applied.
    Revalidate the migrated case on its press: this function does not select a
    family or guarantee that automatic selection on another press is unchanged.
    Inputs are immutable; already canonical cases are rejected to avoid doubling.
    """
    if not isinstance(case, (StudyCase, PlanningCase)):
        raise InvalidProductionInputError("migration requires StudyCase or PlanningCase")
    if type(profiles_per_billet) is not int or profiles_per_billet not in (1, 2):
        raise InvalidProductionInputError("profiles_per_billet must be the verified integer 1 or 2")
    if use_multi_billet_override is not None and type(use_multi_billet_override) is not bool:
        raise InvalidProductionInputError("use_multi_billet_override must be bool or None")
    attr = "production" if isinstance(case, StudyCase) else "process"
    spec = getattr(case, attr)
    if spec.trim_total_per_billet_m is not None:
        raise InvalidProductionInputError("case is already canonical; do not migrate twice")
    override = spec.multi_billet_front_scrap_m
    if override is not None and use_multi_billet_override is None:
        raise InvalidProductionInputError("explicitly choose whether the legacy multi-billet override was applied")
    if use_multi_billet_override and (override is None or profiles_per_billet != 1):
        raise InvalidProductionInputError("multi-billet override requires an existing override and p=1")
    applied = override if use_multi_billet_override else (spec.front_scrap_m or 0.0)
    migrated = replace(spec, front_scrap_m=None, multi_billet_front_scrap_m=None,
                       trim_total_per_billet_m=applied * profiles_per_billet)
    return replace(case, **{attr: migrated})
