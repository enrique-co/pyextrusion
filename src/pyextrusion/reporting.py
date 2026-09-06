from __future__ import annotations

from .demand import AnnualCalculationResult
from .models import CalculationResult, ComparisonResult, PressSpec


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _fmt_optional(value: float | None, pattern: str = ".1f") -> str:
    return "n/a" if value is None else format(value, pattern)


def format_press(press: PressSpec) -> str:
    nominal = "n/a" if press.nominal_size_in is None else f'{press.nominal_size_in:g}"'
    force = "n/a" if press.press_force_t is None else f"{press.press_force_t:.0f} t"
    target = (
        "n/a"
        if press.target_net_productivity_kg_h is None
        else f"{press.target_net_productivity_kg_h:.0f} kg/h ({press.target_productivity_source})"
    )
    return "\n".join([
        f"Press: {press.name}",
        f"  Nominal size:         {nominal} ({press.nominal_size_source})",
        f"  Press force:          {force}",
        f"  Container diameter:   {press.container_diameter_mm:.3f} mm ({press.container_diameter_source})",
        f"  Billet diameter:      {press.billet_diameter_mm:.3f} mm ({press.billet_diameter_source})",
        f"  Billet range:         {press.billet_min_length_mm:.0f} - {press.billet_max_length_mm:.0f} mm ({press.billet_limits_source})",
        f"  Table length:         {press.table_length_m:.2f} m",
        f"  Dead time:            {press.dead_time_sec:.2f} s",
        f"  Aluminium density:    {press.density_kg_m3:.1f} kg/m³",
        f"  Container area:       {press.container_area_m2:.6f} m²",
        f"  Billet area:          {press.billet_area_m2:.6f} m²",
        f"  Billet weight:        {press.billet_weight_kg_per_mm:.6f} kg/mm",
        f"  Saw widths (B/P/F):   {press.saws.billet_mm:.2f} / {press.saws.puller_mm:.2f} / {press.saws.final_mm:.2f} mm",
        f"  Target net output:    {target}",
    ])


def format_result(result: CalculationResult) -> str:
    config = result.recommended_configuration or "none"
    lines = [
        f"PyExtrusion calculation - {result.press_name}",
        "-" * (26 + len(result.press_name)),
        f"Supported:               {_yes_no(result.supported)}",
        f"Viable:                  {_yes_no(result.viable)}",
        f"Recommended config:      {config}",
        f"Extrusion ratio:         {result.extrusion_ratio:.2f}:1",
        f"RE status:               {result.extrusion_ratio_status.upper()}",
        f"Exit speed:              {result.exit_speed_m_min:.3f} m/min ({result.process.speed_input_source})",
        f"Ram speed:               {result.ram_speed_mm_s:.3f} mm/s",
        f"Cuts / billet:           {result.cuts} / {result.theoretical_cuts} theoretical",
        f"Cuts / pull:             {result.cuts_per_pull}",
        f"Billets / pull:          {result.billets_per_pull}",
        f"Pull length / profile:   {result.geometry.profile_pull_length_m:.3f} m",
        f"Extruded / billet:       {result.geometry.extruded_length_per_billet_m:.3f} m",
        f"Table occupancy:         {result.geometry.table_occupancy_length_m:.3f} m",
        f"Billet length:           {result.billet_length_mm:.3f} mm",
        f"Recommended billet:      {result.recommended_billet_length_mm} mm",
        f"Butt discard:            {result.butt_mm:.1f} mm ({result.billet.butt_source})",
        f"Applied front scrap:     {result.process.applied_front_scrap_m:.3f} m ({result.process.applied_front_scrap_source})",
        f"Profiles / billet:       {result.production.profiles_per_billet}",
        f"Bars / billet:           {result.bars_per_billet}",
        f"Bars / full pull:        {result.bars_per_pull}",
        f"Pulls:                   {result.n_pulls}",
        f"Base bars requested:     {result.production.bars_requested}",
        f"Effective bar target:    {result.production.bars_target_effective}",
        f"Billets:                 {result.billets}",
        f"Bars manufactured:       {result.bars_manufactured}",
        f"Good kg manufactured:    {result.good_kg_manufactured:.1f} kg",
        f"Fixed scrap:             {result.fixed_scrap_pct:.2f}% ({result.fixed_scrap_kg:.1f} kg)",
        f"Global scrap:            {result.global_scrap_pct:.2f}% ({result.global_scrap_kg:.1f} kg)",
        f"Nominal gross output:    {result.nominal_gross_kg_h:.1f} kg/h",
        f"Real gross output:       {result.real_gross_kg_h:.1f} kg/h",
        f"Real net output:         {result.real_net_kg_h:.1f} kg/h",
        f"Target net output:       {_fmt_optional(result.target_net_productivity_kg_h, '.1f')} kg/h",
        f"Productivity ratio:      {_fmt_optional(result.productivity_ratio, '.3f')}",
        f"Productivity deficit:    {_fmt_optional(result.productivity_deficit_pct, '.1f')}%",
        f"Productivity index:      {_fmt_optional(result.productivity_index, '.1f')}",
        f"Total time:              {result.total_time_min:.2f} min",
        f"Geometric index:         {result.geometric_index:.2f}",
    ]
    if not result.supported and result.unsupported_reason:
        lines.append(f"Unsupported scenario:    {result.unsupported_reason}")
    if result.productivity.productivity_index_rating is not None:
        lines.append(
            f"Productivity rating:     {result.productivity.productivity_index_rating}"
        )
    if result.supplement_10_pct:
        lines.append("Demand supplement:       10% included")
    if result.valid_configurations:
        lines.append("Valid configurations:    " + ", ".join(result.valid_configurations))
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)


def format_comparison(comparison: ComparisonResult) -> str:
    headers = [
        "Press", "OK", "Configuration", "RE", "RE status", "Billet mm",
        "Net kg/h", "Target", "Prod idx", "Fixed %", "Time h", "Geo idx",
    ]
    rows: list[list[str]] = []
    for r in comparison.results:
        rows.append([
            r.press_name,
            _yes_no(r.viable),
            r.recommended_configuration or "-",
            f"{r.extrusion_ratio:.1f}",
            r.extrusion_ratio_status.upper(),
            f"{r.recommended_billet_length_mm}",
            f"{r.real_net_kg_h:.0f}",
            "-" if r.target_net_productivity_kg_h is None else f"{r.target_net_productivity_kg_h:.0f}",
            "-" if r.productivity_index is None else f"{r.productivity_index:.1f}",
            f"{r.fixed_scrap_pct:.1f}",
            f"{r.total_time_min / 60:.2f}",
            f"{r.geometric_index:.1f}",
        ])
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def render(row: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    out = [render(headers), render(["-" * w for w in widths])]
    out.extend(render(row) for row in rows)
    out.append("")
    out.append(
        "The productivity index is orientative. PyExtrusion does not make the final industrial decision for the user."
    )
    return "\n".join(out)


def format_annual_result(result: AnnualCalculationResult) -> str:
    n = result.normalized
    c = result.calculation
    lines = [
        f"PyExtrusion annual demand - {c.press_name}",
        "-" * (28 + len(c.press_name)),
        f"Demand source:            {result.demand.value:g} {result.demand.unit}/year",
        f"Normalized target:        {n.kg_target:.1f} kg/year",
        f"                         {n.meters_target:.1f} m/year",
        f"                         {n.bars_target} bars/year",
        f"Billets / year:           {result.billets_annual}",
        f"Hours / year:             {result.hours_annual:.2f} h",
        f"Manufactured bars:        {c.bars_manufactured}",
        f"Manufactured good kg:     {c.good_kg_manufactured:.1f} kg",
        f"Real net output:          {c.real_net_kg_h:.1f} kg/h",
        f"Productivity index:       {_fmt_optional(c.productivity_index, '.1f')}",
        f"Recommended config:       {c.recommended_configuration or 'none'}",
    ]
    if n.supplement_10_pct:
        lines.insert(3, f"Adjusted demand:          {n.adjusted_source_value:g} {result.demand.unit}/year")
        lines.append("Demand supplement:        10% included")
    if c.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in c.warnings)
    return "\n".join(lines)


def format_planning_result(result) -> str:
    """Human-readable operational planning summary."""
    r = result
    req = r.request
    if req.mode == "hours":
        request_text = f"{req.value:g} h available"
    elif req.mode == "minutes":
        request_text = f"{req.value:g} min available"
    else:
        request_text = f"{req.value:g} {req.mode}"

    lines = [
        "PyExtrusion production planning",
        "-------------------------------",
        f"Request:                  {request_text}",
        f"Process supported:        {_yes_no(r.process_supported)}",
        f"Process viable:           {_yes_no(r.process_viable)}",
        f"Request fulfilled:        {_yes_no(r.request_fulfilled)}",
        f"Recommended config:       {r.recommended_configuration or 'none'}",
        f"Billets / pull:           {r.billets_per_pull}",
        f"Bars / billet:            {r.bars_per_billet}",
        f"Optimized billet:         {r.billet_length_mm:.2f} mm",
        f"Recommended billet:       {r.recommended_billet_length_mm} mm",
        f"Table occupancy:          {r.table_occupancy_length_m:.2f} m",
        f"Planned billets:          {r.planned_billets}",
        f"Planned pulls:            {r.planned_pulls}",
        f"Planned bars:             {r.planned_bars}",
        f"Planned good metres:      {r.planned_good_m:.2f} m",
        f"Planned good kg:          {r.planned_good_kg:.1f} kg",
        f"Total scrap:              {r.planned_total_scrap_kg:.1f} kg",
        f"Total scrap %:            {r.planned_total_scrap_pct:.2f}%",
        f"Time used:                {r.time_used_min:.2f} min",
    ]
    if r.normalized_target_bars is not None and req.mode in {"kg", "m"}:
        lines.insert(3, f"Normalized bar target:    {r.normalized_target_bars}")
    if r.requested_billets is not None:
        lines.insert(3, f"Requested billets:        {r.requested_billets}")
    if r.available_time_min is not None:
        lines.append(f"Available time:           {r.available_time_min:.2f} min")
        lines.append(f"Time remaining:           {r.time_remaining_min:.2f} min")
        if r.additional_time_for_next_billet_min is not None:
            lines.append(
                f"Extra for next billet:    {r.additional_time_for_next_billet_min:.2f} min"
            )
    lines.append("Complete billets only:    YES")
    if r.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in r.warnings)
    core = r.calculation if r.calculation is not None else r.reference
    if core.warnings:
        lines.append("Core warnings:")
        lines.extend(f"  - {warning}" for warning in core.warnings)
    return "\n".join(lines)


def format_production_sequence(result) -> str:
    """Human-readable continuous technical production-sequence summary."""
    lines = [
        f"PyExtrusion production sequence - {result.press_name}",
        "-" * (34 + len(result.press_name)),
        f"Orders:                   {result.total_orders}",
        f"All orders fulfilled:     {_yes_no(result.all_orders_fulfilled)}",
        f"Total billets:            {result.total_planned_billets}",
        f"Total pulls:              {result.total_planned_pulls}",
        f"Total bars:               {result.total_planned_bars}",
        f"Total good metres:        {result.total_planned_good_m:.2f} m",
        f"Total good kg:            {result.total_planned_good_kg:.1f} kg",
        f"Total scrap:              {result.total_scrap_kg:.1f} kg",
        f"Technical press time:     {result.total_press_time_min:.2f} min ({result.total_press_hours:.2f} h)",
    ]
    if result.start_at is not None:
        lines.append(f"Theoretical start:        {result.start_at.isoformat()}")
        lines.append(f"Theoretical end:          {result.theoretical_end_at.isoformat()}")
    lines.append("")
    lines.append("Orders (input order preserved):")
    for entry in result.orders:
        status = "OK" if entry.request_fulfilled else "UNRESOLVED"
        clock = ""
        if entry.theoretical_start_at is not None:
            clock = f" | {entry.theoretical_start_at.isoformat()} -> {entry.theoretical_end_at.isoformat()}"
        lines.append(
            f"  {entry.index}. {entry.order_id}: {status} | "
            f"{entry.duration_min:.2f} min | cumulative "
            f"{entry.cumulative_start_min:.2f} -> {entry.cumulative_end_min:.2f} min | "
            f"{entry.planned_billets} billets | {entry.planned_bars} bars{clock}"
        )
    if result.unresolved_order_ids:
        lines.append("Unresolved orders:        " + ", ".join(result.unresolved_order_ids))
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render(row: list[str]) -> str:
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))

    output = [render(headers), render(["-" * width for width in widths])]
    output.extend(render(row) for row in rows)
    return "\n".join(output)


def format_process_comparison(comparison) -> str:
    """Human-readable quantity-free multi-press process comparison."""
    headers = [
        "Press", "Supported", "Viable", "Configuration", "RE", "Exit m/min",
        "Billet mm", "Billets/pull", "Bars/billet", "First billet min", "Geo idx",
    ]
    rows: list[list[str]] = []
    for result in comparison.results:
        rows.append([
            result.press_name,
            _yes_no(result.supported),
            _yes_no(result.viable),
            result.recommended_configuration or "-",
            f"{result.extrusion_ratio:.1f}",
            f"{result.exit_speed_m_min:.2f}",
            f"{result.recommended_billet_length_mm}",
            str(result.billets_per_pull),
            str(result.bars_per_billet),
            f"{result.first_billet_time_min:.2f}",
            f"{result.geometric_index:.1f}",
        ])
    return _render_table(headers, rows) + (
        "\n\nPyExtrusion preserves press order and does not rank presses or declare an automatic winner."
    )


def format_planning_comparison(comparison) -> str:
    """Human-readable multi-press comparison for one explicit PlanningRequest."""
    headers = [
        "Press", "Process OK", "Request OK", "Configuration", "Billets", "Pulls",
        "Bars", "Good kg", "Scrap kg", "Time h", "Billet mm",
    ]
    rows: list[list[str]] = []
    for result in comparison.results:
        rows.append([
            result.press_name,
            _yes_no(result.process_viable),
            _yes_no(result.request_fulfilled),
            result.recommended_configuration or "-",
            str(result.planned_billets),
            str(result.planned_pulls),
            str(result.planned_bars),
            f"{result.planned_good_kg:.1f}",
            f"{result.planned_total_scrap_kg:.1f}",
            f"{result.planned_hours:.2f}",
            str(result.recommended_billet_length_mm),
        ])
    return _render_table(headers, rows) + (
        "\n\nThe same PlanningCase and PlanningRequest are applied to every press. "
        "PyExtrusion does not rank presses or declare an automatic winner."
    )


def format_production_sequence_comparison(comparison) -> str:
    """Human-readable comparison of the exact same order sequence on several presses."""
    headers = [
        "Press", "All orders OK", "Unresolved", "Billets", "Pulls", "Bars",
        "Good kg", "Scrap kg", "Tech time h", "Theoretical end",
    ]
    rows: list[list[str]] = []
    for result in comparison.results:
        rows.append([
            result.press_name,
            _yes_no(result.all_orders_fulfilled),
            str(len(result.unresolved_order_ids)),
            str(result.total_planned_billets),
            str(result.total_planned_pulls),
            str(result.total_planned_bars),
            f"{result.total_planned_good_kg:.1f}",
            f"{result.total_scrap_kg:.1f}",
            f"{result.total_press_hours:.2f}",
            result.theoretical_end_at.isoformat() if result.theoretical_end_at is not None else "-",
        ])
    return _render_table(headers, rows) + (
        "\n\nEach press receives the exact same order list in the exact same order. "
        "No allocation, reordering, external plant time or automatic winner is introduced."
    )
