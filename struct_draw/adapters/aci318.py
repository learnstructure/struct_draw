"""struct_draw.adapters.aci318 — Translate ACI 318 results to dataclasses.

This adapter reads ``aci318`` result objects **by attribute name
only** — it does not import ``aci318`` itself. That keeps
``struct_draw`` decoupled from the producer and lets the adapter
work with any object that exposes the documented fields.

For each member type the adapter exposes a single
``from_<member>_result(result) -> DataClass`` function:

* :func:`from_beam_result` — reads a ``BeamDesignResult`` /
  ``BeamDetailingResult`` pair and returns a
  :class:`struct_draw.core.data.BeamData`.
* :func:`from_isolated_footing_result` — reads an ``IsolatedFootingDesignResult``
  and returns a :class:`struct_draw.core.data.IsolatedFootingData`.
* :func:`from_combined_footing_result` — reads a ``CombinedFootingDesignResult``
  and returns a :class:`struct_draw.core.data.CombinedFootingData`.
* :func:`from_column_result` — reads a ``ColumnDesignResult`` and
  returns a :class:`struct_draw.core.data.ColumnData`.
* :func:`from_staircase_result` — reads a ``StaircaseDesignResult``
  and returns a :class:`struct_draw.core.data.StaircaseData`.
* :func:`from_slab_result` — reads a ``SlabDesignResult`` and
  returns a :class:`struct_draw.core.data.SlabData`.

The adapters tolerate missing fields: every field is read through
:func:`_safe_getattr` with a default, so a partial producer
result still produces a valid (if sparse) dataclass.
"""

from __future__ import annotations

from typing import Any

from struct_draw.core.data import (
    BeamData,
    ColumnData,
    CombinedFootingData,
    FootingData,
    GeometrySection,
    IsolatedFootingData,
    Rebar,
    ScheduleRow,
    SlabData,
    StaircaseData,
    Stirrup,
)
from struct_draw.core.units import (
    DrawingScale,
    DrawingUnit,
    SCALE_1_2_IN,
    SCALE_1_4_IN,
    SCALE_1_IN,
    SCALE_1_8_IN,
)



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    """``getattr`` that swallows ``AttributeError`` and returns ``default``."""
    try:
        return getattr(obj, name)
    except AttributeError:
        return default


def _section_from(obj: Any) -> GeometrySection:
    """Build a :class:`GeometrySection` from an object with width/depth/cover."""
    return GeometrySection(
        width_in=float(_safe_getattr(obj, "width", 0.0) or 0.0),
        depth_in=float(_safe_getattr(obj, "depth", 0.0) or 0.0),
        cover_in=float(_safe_getattr(obj, "cover", 1.5) or 1.5),
    )


def _stirrup_from(obj: Any) -> Stirrup:
    """Build a :class:`Stirrup` from a shear / stirrup result object."""
    return Stirrup(
        size=str(_safe_getattr(obj, "size", _safe_getattr(obj, "stirrup_size", "#3")) or "#3"),
        spacing_in=float(_safe_getattr(obj, "spacing", _safe_getattr(obj, "stirrup_spacing", 6.0)) or 6.0),
        legs=int(_safe_getattr(obj, "legs", 2) or 2),
        width_in=float(_safe_getattr(obj, "width", 0.0) or 0.0),
        height_in=float(_safe_getattr(obj, "height", 0.0) or 0.0),
    )


def _rebar_from(obj: Any) -> Rebar:
    """Build a :class:`Rebar` from a producer-side bar object."""
    return Rebar(
        mark=str(_safe_getattr(obj, "mark", "B1") or "B1"),
        size=str(_safe_getattr(obj, "size", "#5") or "#5"),
        quantity=int(_safe_getattr(obj, "quantity", 1) or 1),
        length_in=float(_safe_getattr(obj, "length", 0.0) or 0.0),
        points=tuple(_safe_getattr(obj, "points", []) or ()),
        hook_start=bool(_safe_getattr(obj, "hook_start", False)),
        hook_end=bool(_safe_getattr(obj, "hook_end", False)),
        remarks=str(_safe_getattr(obj, "remarks", "") or ""),
    )


def _schedule_from(obj: Any) -> ScheduleRow:
    """Build a :class:`ScheduleRow` from a producer-side schedule row."""
    return ScheduleRow(
        mark=str(_safe_getattr(obj, "mark", "") or ""),
        size=str(_safe_getattr(obj, "size", "") or ""),
        quantity=int(_safe_getattr(obj, "qty", _safe_getattr(obj, "quantity", 0)) or 0),
        length_in=float(_safe_getattr(obj, "length", 0.0) or 0.0),
        remarks=str(_safe_getattr(obj, "remarks", "") or ""),
    )


# ---------------------------------------------------------------------------
# from_*_result functions
# ---------------------------------------------------------------------------


def from_beam_result(result: Any) -> BeamData:
    """Translate an ACI 318 beam result into :class:`BeamData`.

    ``result`` may be either a single combined object or a
    tuple ``(design, detailing)``. The adapter tries both.
    """
    design, detailing = _split_pair(result)
    section = _section_from(_safe_getattr(design, "section", None) or design)

    stirrups = _stirrup_from(
        _safe_getattr(design, "shear", None)
        or _safe_getattr(detailing, "stirrup", None)
        or design
    )

    top_bars = [
        _rebar_from(b)
        for b in (
            list(_safe_getattr(detailing, "top_bars", []) or ())
            or list(_safe_getattr(design, "top_bars", []) or ())
        )
    ] or [
        _placeholder_top_bar(section)
    ]
    bottom_bars = [
        _rebar_from(b)
        for b in (
            list(_safe_getattr(detailing, "bottom_bars", []) or ())
            or list(_safe_getattr(design, "bottom_bars", []) or ())
        )
    ] or [
        _placeholder_bottom_bar(section)
    ]

    schedule = [
        _schedule_from(row)
        for row in (_safe_getattr(detailing, "schedule_rows", []) or ())
    ]

    return BeamData(
        name=str(_safe_getattr(design, "name", _safe_getattr(detailing, "name", "B1")) or "B1"),
        section=section,
        top_bars=tuple(top_bars),
        bottom_bars=tuple(bottom_bars),
        stirrups=stirrups,
        schedule=tuple(schedule),
        length_in=float(_safe_getattr(design, "length", 240.0) or 240.0),
        scale=SCALE_1_2_IN,
        unit=DrawingUnit.IN,
    )


def from_isolated_footing_result(result: Any) -> IsolatedFootingData:
    """Translate an ACI 318 isolated footing result into :class:`IsolatedFootingData`."""
    coordinator = None
    if isinstance(result, tuple) and len(result) == 2:
        elem1, elem2 = result
        if hasattr(elem1, "col_c1") or hasattr(elem1, "concrete"):
            coordinator, design = elem1, elem2
            detailing = _safe_getattr(elem2, "detailing", None)
        elif hasattr(elem2, "col_c1") or hasattr(elem2, "concrete"):
            coordinator, design = elem2, elem1
            detailing = _safe_getattr(elem1, "detailing", None)
        else:
            design, detailing = elem1, elem2
    else:
        design = result
        detailing = _safe_getattr(design, "detailing", None)

    name = str(
        _safe_getattr(design, "name", None)
        or _safe_getattr(design, "member_id", None)
        or _safe_getattr(coordinator, "member_id", None)
        or _safe_getattr(detailing, "member_id", "F1")
        or "F1"
    )

    raw_l = float(_safe_getattr(design, "length_in", None) or _safe_getattr(design, "length", 64.0) or 64.0)
    length_in = raw_l * 12.0 if raw_l <= 30.0 else raw_l

    raw_w = float(_safe_getattr(design, "width_in", None) or _safe_getattr(design, "width", 64.0) or 64.0)
    width_in = raw_w * 12.0 if raw_w <= 30.0 else raw_w

    thickness = float(
        _safe_getattr(design, "mid_thickness", None)
        or _safe_getattr(design, "thickness", None)
        or _safe_getattr(coordinator, "thickness", 16.0)
        or 16.0
    )
    edge_thickness = float(
        _safe_getattr(design, "edge_thickness", None)
        or thickness
    )

    col_w = float(
        _safe_getattr(design, "column_width", None)
        or _safe_getattr(coordinator, "col_c1", None)
        or 14.0
    )
    col_d = float(
        _safe_getattr(design, "column_depth", None)
        or _safe_getattr(coordinator, "col_c2", None)
        or 14.0
    )

    cover = float(
        _safe_getattr(design, "cover", None)
        or _safe_getattr(coordinator, "cover", 3.0)
        or 3.0
    )

    bar_dia = 0.5
    bar_spacing = 6.0
    if detailing and hasattr(detailing, "bars") and detailing.bars:
        first_bar = detailing.bars[0]
        bsize = str(_safe_getattr(first_bar, "bar_size", "#6"))
        if bsize.startswith("#"):
            try:
                bar_dia = int(bsize[1:]) / 8.0
            except ValueError:
                bar_dia = 0.5
        bar_count = int(_safe_getattr(first_bar, "count", 0))
        if bar_count > 1 and width_in > 2 * cover:
            bar_spacing = round((width_in - 2 * cover) / (bar_count - 1), 1)

    bar_dia_in = float(_safe_getattr(design, "bar_dia", bar_dia) or bar_dia)
    bar_spacing_in = float(_safe_getattr(design, "bar_spacing", bar_spacing) or bar_spacing)

    col_bars_raw = _safe_getattr(detailing, "column_bars", None)
    if col_bars_raw:
        col_bars = tuple(_rebar_from(b) for b in col_bars_raw)
    else:
        col_bars = (
            Rebar(mark="CB1", size="#8", quantity=4, length_in=120.0, remarks="Column Starter Dowels"),
        )

    col_stirrup = _stirrup_from(
        _safe_getattr(detailing, "column_stirrup", None)
        or _safe_getattr(design, "column_stirrup", None)
        or Stirrup(size="#4", spacing_in=6.0, legs=2)
    )

    ld = float(
        _safe_getattr(design, "Ld", None)
        or _safe_getattr(design, "development_length", None)
        or 24.0
    )

    return IsolatedFootingData(
        name=name,
        length_in=length_in,
        width_in=width_in,
        mid_thickness_in=thickness,
        edge_thickness_in=edge_thickness,
        column_width_in=col_w,
        column_depth_in=col_d,
        column_height_in=float(_safe_getattr(design, "column_height", 84.0) or 84.0),
        footing_depth_in=float(_safe_getattr(design, "footing_depth", 60.0) or 60.0),
        plinth_height_in=float(_safe_getattr(design, "plinth_height", 24.0) or 24.0),
        cover_in=cover,
        bar_dia_in=bar_dia_in,
        bar_spacing_in=bar_spacing_in,
        column_bars=col_bars,
        column_stirrups=col_stirrup,
        development_length_in=ld,
        scale=SCALE_1_2_IN,
        unit=DrawingUnit.IN,
    )


def from_combined_footing_result(result: Any) -> CombinedFootingData:
    """Translate an ACI 318 combined footing result into :class:`CombinedFootingData`."""
    coordinator = None
    if isinstance(result, tuple) and len(result) == 2:
        elem1, elem2 = result
        if hasattr(elem1, "col1_c1") or hasattr(elem1, "column_spacing_ft") or hasattr(elem1, "concrete"):
            coordinator, design = elem1, elem2
            detailing = _safe_getattr(elem2, "detailing", None)
        elif hasattr(elem2, "col1_c1") or hasattr(elem2, "column_spacing_ft") or hasattr(elem2, "concrete"):
            coordinator, design = elem2, elem1
            detailing = _safe_getattr(elem1, "detailing", None)
        else:
            design, detailing = elem1, elem2
    else:
        design = result
        detailing = _safe_getattr(design, "detailing", None)

    name = str(
        _safe_getattr(design, "name", None)
        or _safe_getattr(design, "member_id", None)
        or _safe_getattr(coordinator, "member_id", None)
        or _safe_getattr(detailing, "member_id", "CF1")
        or "CF1"
    )

    raw_l = float(_safe_getattr(design, "length_in", None) or _safe_getattr(design, "length", 140.0) or 140.0)
    total_length_in = raw_l * 12.0 if raw_l <= 30.0 else raw_l

    raw_w = float(_safe_getattr(design, "width_in", None) or _safe_getattr(design, "width", 64.0) or 64.0)
    width_in = raw_w * 12.0 if raw_w <= 30.0 else raw_w

    thickness_in = float(
        _safe_getattr(design, "thickness", None)
        or _safe_getattr(coordinator, "thickness", 24.0)
        or 24.0
    )

    raw_col_spacing = float(
        _safe_getattr(coordinator, "column_spacing_ft", None)
        or _safe_getattr(design, "col_spacing_ft", None)
        or 0.0
    )
    if raw_col_spacing > 0.0:
        col_spacing_in = raw_col_spacing * 12.0
    else:
        col_spacing_in = float(
            _safe_getattr(design, "col_spacing_in", None)
            or _safe_getattr(design, "col_spacing", 32.0)
            or 32.0
        )

    raw_cant_col1 = float(
        _safe_getattr(coordinator, "cantilever_col1_ft", None)
        or _safe_getattr(design, "cantilever_col1_ft", None)
        or 0.0
    )
    if raw_cant_col1 > 0.0:
        proj_left_in = raw_cant_col1 * 12.0
    else:
        proj_left_in = float(
            _safe_getattr(design, "proj_left_in", None)
            or _safe_getattr(design, "proj_left", 60.0)
            or 60.0
        )

    if total_length_in > (proj_left_in + col_spacing_in):
        proj_right_in = total_length_in - proj_left_in - col_spacing_in
    else:
        proj_right_in = float(
            _safe_getattr(design, "proj_right_in", None)
            or _safe_getattr(design, "proj_right", 48.0)
            or 48.0
        )

    col1_w = float(
        _safe_getattr(coordinator, "col1_c1", None)
        or _safe_getattr(design, "col1_width", 14.0)
        or 14.0
    )
    col1_d = float(
        _safe_getattr(coordinator, "col1_c2", None)
        or _safe_getattr(design, "col1_depth", 14.0)
        or 14.0
    )
    col2_w = float(
        _safe_getattr(coordinator, "col2_c1", None)
        or _safe_getattr(design, "col2_width", 14.0)
        or 14.0
    )
    col2_d = float(
        _safe_getattr(coordinator, "col2_c2", None)
        or _safe_getattr(design, "col2_depth", 14.0)
        or 14.0
    )

    cover_in = float(
        _safe_getattr(coordinator, "cover", None)
        or _safe_getattr(design, "cover", 3.0)
        or 3.0
    )

    bar_dia = 0.5
    bar_spacing = 6.0
    top_bar_dia = None
    top_bar_spacing = None

    if detailing and hasattr(detailing, "bars") and detailing.bars:
        for bar in detailing.bars:
            loc = str(_safe_getattr(bar, "location", "")).lower()
            bsize = str(_safe_getattr(bar, "bar_size", "#8"))
            dia = 0.5
            if bsize.startswith("#"):
                try:
                    dia = int(bsize[1:]) / 8.0
                except ValueError:
                    dia = 0.5
            cnt = int(_safe_getattr(bar, "count", 0))
            spc = 6.0
            if cnt > 1 and width_in > 2 * cover_in:
                spc = round((width_in - 2 * cover_in) / (cnt - 1), 1)

            if "top" in loc:
                top_bar_dia = dia
                top_bar_spacing = spc
            else:
                bar_dia = dia
                bar_spacing = spc

    bar_dia_in = float(_safe_getattr(design, "bar_dia", bar_dia) or bar_dia)
    bar_spacing_in = float(_safe_getattr(design, "bar_spacing", bar_spacing) or bar_spacing)
    if top_bar_dia is not None:
        top_bar_dia_in = float(_safe_getattr(design, "top_bar_dia", top_bar_dia) or top_bar_dia)
        top_bar_spacing_in = float(_safe_getattr(design, "top_bar_spacing", top_bar_spacing) or top_bar_spacing)
    else:
        top_bar_dia_in = None
        top_bar_spacing_in = None

    col_bars_raw = _safe_getattr(detailing, "column_bars", None)
    if col_bars_raw:
        col_bars = tuple(_rebar_from(b) for b in col_bars_raw)
    else:
        col_bars = (
            Rebar(mark="CB1", size="#8", quantity=4, length_in=120.0, remarks="Col 1 Starter Dowels"),
            Rebar(mark="CB2", size="#8", quantity=4, length_in=120.0, remarks="Col 2 Starter Dowels"),
        )

    col_stirrup = _stirrup_from(
        _safe_getattr(detailing, "column_stirrup", None)
        or _safe_getattr(design, "column_stirrup", None)
        or Stirrup(size="#4", spacing_in=6.0, legs=2)
    )

    ld = float(
        _safe_getattr(design, "Ld", None)
        or _safe_getattr(design, "development_length", None)
        or 24.0
    )

    return CombinedFootingData(
        name=name,
        proj_left_in=proj_left_in,
        proj_right_in=proj_right_in,
        col_spacing_in=col_spacing_in,
        width_in=width_in,
        thickness_in=thickness_in,
        col1_width_in=col1_w,
        col1_depth_in=col1_d,
        col2_width_in=col2_w,
        col2_depth_in=col2_d,
        footing_depth_in=float(_safe_getattr(design, "footing_depth", 60.0) or 60.0),
        plinth_height_in=float(_safe_getattr(design, "plinth_height", 24.0) or 24.0),
        cover_in=cover_in,
        bar_dia_in=bar_dia_in,
        bar_spacing_in=bar_spacing_in,
        top_bar_dia_in=top_bar_dia_in,
        top_bar_spacing_in=top_bar_spacing_in,
        column_bars=col_bars,
        column_stirrups=col_stirrup,
        development_length_in=ld,
        scale=SCALE_1_2_IN,
        unit=DrawingUnit.IN,
    )


def from_column_result(result: Any) -> ColumnData:
    """Translate an ACI 318 column result into :class:`ColumnData`."""
    design = result[0] if isinstance(result, tuple) else result
    detailing = result[1] if isinstance(result, tuple) else _safe_getattr(design, "detailing", None)
    section = _section_from(_safe_getattr(design, "section", None) or design)
    return ColumnData(
        name=str(_safe_getattr(design, "name", "C1") or "C1"),
        section=section,
        height_in=float(_safe_getattr(design, "height", 120.0) or 120.0),
        longitudinal_bars=tuple(
            _rebar_from(b) for b in (_safe_getattr(detailing, "longitudinal_bars", []) or ())
        ),
        stirrups=_stirrup_from(_safe_getattr(detailing, "stirrup", None) or design),
        schedule=tuple(
            _schedule_from(row) for row in (_safe_getattr(detailing, "schedule_rows", []) or ())
        ),
        scale=SCALE_1_4_IN,
        unit=DrawingUnit.IN,
    )


def from_staircase_result(result: Any) -> StaircaseData:
    """Translate an ACI 318 staircase result into :class:`StaircaseData`."""
    design = result[0] if isinstance(result, tuple) else result
    return StaircaseData(
        name=str(_safe_getattr(design, "name", "ST1") or "ST1"),
        flight_width_in=float(_safe_getattr(design, "flight_width", 48.0) or 48.0),
        flight_length_in=float(_safe_getattr(design, "flight_length", 120.0) or 120.0),
        riser_height_in=float(_safe_getattr(design, "riser_height", 7.0) or 7.0),
        tread_depth_in=float(_safe_getattr(design, "tread_depth", 11.0) or 11.0),
        slab_thickness_in=float(_safe_getattr(design, "slab_thickness", 6.0) or 6.0),
        landings=int(_safe_getattr(design, "landings", 1) or 1),
        scale=SCALE_1_IN,
        unit=DrawingUnit.IN,
    )


def from_slab_result(result: Any) -> SlabData:
    """Translate an ACI 318 slab result into :class:`SlabData`."""
    design = result[0] if isinstance(result, tuple) else result
    detailing = result[1] if isinstance(result, tuple) else _safe_getattr(design, "detailing", None)
    top_bar_obj = _safe_getattr(detailing, "top_bar", None)
    bot_bar_obj = _safe_getattr(detailing, "bottom_bar", None)
    return SlabData(
        name=str(_safe_getattr(design, "name", "S1") or "S1"),
        length_in=float(_safe_getattr(design, "length", 240.0) or 240.0),
        width_in=float(_safe_getattr(design, "width", 120.0) or 120.0),
        thickness_in=float(_safe_getattr(design, "thickness", 6.0) or 6.0),
        cover_in=float(_safe_getattr(design, "cover", 0.75) or 0.75),
        top_bar=_rebar_from(top_bar_obj) if top_bar_obj is not None else None,
        bottom_bar=_rebar_from(bot_bar_obj) if bot_bar_obj is not None else None,
        scale=SCALE_1_8_IN,
        unit=DrawingUnit.IN,
    )


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------


def _split_pair(result: Any) -> tuple[Any, Any]:
    """Return ``(design, detailing)`` whether ``result`` is one or both."""
    if isinstance(result, tuple) and len(result) == 2:
        return result
    design = result
    detailing = _safe_getattr(result, "detailing", None)
    return design, detailing


def _placeholder_top_bar(section: GeometrySection) -> Rebar:
    """Two ``#5`` bars as a sensible default for an empty top-bar list."""
    return Rebar(mark="T1", size="#5", quantity=2, length_in=section.width_in - 2 * section.cover_in)


def _placeholder_bottom_bar(section: GeometrySection) -> Rebar:
    """Two ``#5`` bars as a sensible default for an empty bottom-bar list."""
    return Rebar(mark="B1", size="#5", quantity=2, length_in=section.width_in - 2 * section.cover_in)


__all__ = [
    "from_beam_result",
    "from_isolated_footing_result",
    "from_combined_footing_result",
    "from_column_result",
    "from_staircase_result",
    "from_slab_result",
]