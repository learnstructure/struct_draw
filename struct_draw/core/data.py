"""struct_draw.core.data — Plain drawing-side data classes.

These dataclasses are the **contract** between ``struct_draw`` and the
rest of the Structural Engineering Ecosystem. Adapters (``aci318``
today, ``fem2d`` tomorrow) translate producer-side result objects
into these classes; element functions consume them.

The dataclasses are intentionally:

* **plain** — no behavior, no default drawing,
* **complete** — they carry everything an element function needs
  to draw a member end-to-end (concrete outline, rebar layout,
  stirrups, schedule rows, level markers, etc.),
* **decoupled** — they do not import from ``aci318`` or any other
  producer; they reference concrete rebar sizes / quantities as
  floats / ints / strings, not as engineering objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


Point = tuple[float, float]


def _resolve_unit_is_metric(unit: Any, fallback: bool) -> bool:
    """Safely determine if unit is metric, handling DrawingUnit, string, or None."""
    if unit is None:
        return fallback
    if isinstance(unit, str):
        u = unit.strip().lower()
        if u in ("in", "inch", "inches", "ft", "foot", "feet"):
            return False
        if u in ("mm", "cm", "m", "meter", "meters"):
            return True
    return getattr(unit, "is_metric", fallback)


# ---------------------------------------------------------------------------
# Bar / stirrup supporting classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rebar:
    """A single straight or simple-shape rebar.

    Attributes
    ----------
    mark
        Bar mark label (e.g. ``"B1"``). Shown in the bar schedule.
    size
        Bar diameter designator (e.g. ``"#5"``, ``"16mm"``). Shown
        as a string exactly as produced by the producer.
    quantity
        Number of identical bars in the group.
    length_in
        Total developed length of the bar (inches).
    points
        Sequence of ``(x, y)`` points drawing the bar's polyline
        (in drawing units). An empty list means "no geometry yet".
    hook_start / hook_end
        Whether the bar has a standard 90° / 135° hook at the
        start / end of its polyline.
    remarks
        Free-form schedule remarks ("TOP", "BOT", "EA. FACE", …).
    """

    mark: str
    size: str = "#5"
    quantity: int = 1
    length_in: float = 0.0
    points: Sequence[Point] = field(default_factory=tuple)
    hook_start: bool = False
    hook_end: bool = False
    remarks: str = ""


@dataclass(frozen=True)
class Stirrup:
    """A stirrup / tie / hoop description.

    Attributes
    ----------
    size
        Stirrup bar designator (e.g. ``"#3"``, ``"8mm"``).
    spacing_in
        Spacing along the member (inches).
    legs
        Number of legs (2 for a single rectangular stirrup).
    width_in / height_in
        Stirrup outer dimensions (inches).
    """

    size: str = "#3"
    spacing_in: float = 6.0
    legs: int = 2
    width_in: float = 0.0
    height_in: float = 0.0
    zone_type: str | None = None
    start_zone: float = 0.0
    end_zone: float = 0.0


@dataclass(frozen=True)
class ScheduleRow:
    """One row in the bar schedule (a ``ScheduleRow`` table line)."""

    mark: str
    size: str
    quantity: int
    length_in: float
    remarks: str = ""
    shape_code: str = ""
    unit_weight: float | None = None
    total_weight: float | None = None


@dataclass(frozen=True)
class ScheduleTableData:
    """All information needed to draw a bar bending schedule table.

    Attributes
    ----------
    title
        Heading text for the table (e.g. ``"BAR BENDING SCHEDULE"``).
    rows
        Sequence of :class:`ScheduleRow` objects.
    unit
        Drawing unit (e.g. ``DrawingUnit.MM``, ``DrawingUnit.IN``).
    scale
        Drawing scale (e.g. ``"1:50"``, ``"1/4\"=1'-0\""``).
    include_weights
        Whether to calculate and display unit weights and total weights.
    total_weight
        Explicit override for total weight (lbs or kg). If None, calculated automatically.
    remarks
        Optional notes or remarks rendered under the table.
    """

    title: str = "BAR BENDING SCHEDULE"
    rows: Sequence[ScheduleRow] = field(default_factory=tuple)
    unit: Any = None
    scale: Any = None
    include_weights: bool = True
    total_weight: float | None = None
    remarks: str = ""

    @property
    def is_metric(self) -> bool:
        """True if the table is formatted in SI metric units."""
        return _resolve_unit_is_metric(self.unit, False)


@dataclass(frozen=True)
class GeometrySection:
    """A rectangular concrete cross-section description.

    Attributes
    ----------
    width_in / depth_in
        Section dimensions (inches).
    cover_in
        Clear cover to the outer stirrup (inches).
    """

    width_in: float = 0.0
    depth_in: float = 0.0
    cover_in: float = 1.5


# ---------------------------------------------------------------------------
# Top-level member data classes (one per element module)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BeamData:
    """All information needed to draw a beam (section + elevation).

    Attributes
    ----------
    name
        Beam identifier (e.g. ``"B1"``).
    section
        :class:`GeometrySection` description.
    top_bars / bottom_bars
        Sequences of :class:`Rebar` for the top and bottom
        longitudinal layers.
    stirrups
        :class:`Stirrup` description (one type per beam, typical).
    schedule
        Sequence of :class:`ScheduleRow` for the bar schedule.
    length_in
        Total beam length, used for the elevation view.
    """

    name: str = "B1"
    section: GeometrySection = field(default_factory=GeometrySection)
    top_bars: Sequence[Rebar] = field(default_factory=tuple)
    bottom_bars: Sequence[Rebar] = field(default_factory=tuple)
    stirrups: Stirrup = field(default_factory=Stirrup)
    schedule: Sequence[ScheduleRow] = field(default_factory=tuple)
    length_in: float = 240.0
    scale: Any = None
    unit: Any = None

    @property
    def is_metric(self) -> bool:
        """True if the beam dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(self.unit, self.section.width_in >= 100.0 or self.section.depth_in >= 100.0)


@dataclass(frozen=True)
class BeamProfileSpan:
    """Description of a single span in a multi-span continuous beam profile.

    Attributes
    ----------
    length_in
        Clear or center-to-center span length (inches or mm).
    support_stirrup_spacing_in
        Stirrup spacing near supports (inches or mm).
    mid_stirrup_spacing_in
        Stirrup spacing in mid-span region (inches or mm).
    top_extra_bars
        Sequence of Rebar for top support reinforcement.
    bottom_bars
        Sequence of Rebar for bottom flexural reinforcement.
    """

    length_in: float = 216.0
    support_stirrup_spacing_in: float = 4.0
    mid_stirrup_spacing_in: float = 6.0
    top_extra_bars: Sequence[Rebar] = field(default_factory=tuple)
    bottom_bars: Sequence[Rebar] = field(default_factory=tuple)


@dataclass(frozen=True)
class BeamProfileData:
    """All information needed to draw a continuous multi-span beam profile (longitudinal section).

    Attributes
    ----------
    name
        Beam profile identifier (e.g. ``"L-SECTION OF BEAM ALONG GRIDS A-A"``).
    grid_line_name
        Grid line label (e.g. ``"A-A"``).
    spans_in
        Sequence of span lengths (in inches or mm). Default corresponds to SI metric 5.5m, 4m, 3m, 4m, 5.5m.
    col_width_in
        Column width at supports (inches or mm).
    beam_width_in
        Beam cross-section width (inches or mm).
    beam_depth_in
        Beam cross-section depth/height (inches or mm).
    cover_in
        Concrete clear cover (inches or mm).
    col_extension_in
        Column vertical extension above/below the beam (inches or mm).
    grid_extension_in
        Grid line extension beyond column top (inches or mm).
    grid_labels
        Custom grid labels tuple (e.g. ``("A", "B", "C", "D", "E", "F")``). If empty, auto-generated A, B, C...
    level_text
        Level marker text label (e.g. ``"PL+3.0 m"``).
    top_bars
        Sequence of Rebar for continuous top longitudinal reinforcement.
    bottom_bars
        Sequence of Rebar for continuous bottom longitudinal reinforcement.
    top_extra_bars
        Sequence of Rebar for top support reinforcement over columns.
    stirrup
        Stirrup description.
    support_stirrup_spacing_in
        Default stirrup spacing near support zones (inches or mm).
    mid_stirrup_spacing_in
        Default stirrup spacing in mid-span zones (inches or mm).
    """

    name: str = "B1"
    grid_line_name: str = "A-A"
    spans_in: Sequence[float] = (216.0, 180.0, 216.0)
    col_width_in: float = 18.0
    beam_width_in: float = 18.0
    beam_depth_in: float = 18.0
    cover_in: float = 1.5
    col_extension_in: float = 38.0
    grid_extension_in: float = 60.0
    grid_labels: Sequence[str] = field(default_factory=tuple)
    level_text: str = "PL+3.0 m"
    top_bars: Sequence[Rebar] = field(default_factory=tuple)
    bottom_bars: Sequence[Rebar] = field(default_factory=tuple)
    top_extra_bars: Sequence[Rebar] = field(default_factory=tuple)
    stirrup: Stirrup = field(default_factory=Stirrup)
    support_stirrup_spacing_in: float = 4.0
    mid_stirrup_spacing_in: float = 6.0
    scale: Any = None
    unit: Any = None

    @property
    def is_metric(self) -> bool:
        """True if dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(self.unit, self.beam_depth_in >= 100.0 or (len(self.spans_in) > 0 and self.spans_in[0] >= 300.0))

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "PB-1",
        grid_line_name: str = "A-A",
        spans: Sequence[float] | None = None,
        col_width: float | None = None,
        beam_width: float | None = None,
        beam_depth: float | None = None,
        cover: float | None = None,
        col_extension: float | None = None,
        grid_extension: float | None = None,
        grid_labels: Sequence[str] = (),
        level_text: str = "PL+3.0 m",
        top_bars: Sequence[Rebar] = (),
        bottom_bars: Sequence[Rebar] = (),
        top_extra_bars: Sequence[Rebar] = (),
        stirrup: Stirrup | None = None,
        support_stirrup_spacing: float | None = None,
        mid_stirrup_spacing: float | None = None,
        scale: Any = None,
        unit: Any = None,
    ) -> BeamProfileData:
        """Construct BeamProfileData directly from SI metric parameters."""
        _spans = spans if spans is not None else (5500.0, 4000.0, 3000.0, 4000.0, 5500.0)
        _col_width = col_width if col_width is not None else 450.0
        _beam_width = beam_width if beam_width is not None else 450.0
        _beam_depth = beam_depth if beam_depth is not None else 450.0
        _cover = cover if cover is not None else 40.0
        _col_extension = col_extension if col_extension is not None else 975.0
        _grid_extension = grid_extension if grid_extension is not None else 1500.0
        _supp_spacing = support_stirrup_spacing if support_stirrup_spacing is not None else 100.0
        _mid_spacing = mid_stirrup_spacing if mid_stirrup_spacing is not None else 150.0

        return cls(
            name=name,
            grid_line_name=grid_line_name,
            spans_in=tuple(_spans),
            col_width_in=_col_width,
            beam_width_in=_beam_width,
            beam_depth_in=_beam_depth,
            cover_in=_cover,
            col_extension_in=_col_extension,
            grid_extension_in=_grid_extension,
            grid_labels=tuple(grid_labels),
            level_text=level_text,
            top_bars=top_bars,
            bottom_bars=bottom_bars,
            top_extra_bars=top_extra_bars,
            stirrup=stirrup or Stirrup(size="10mm dia", spacing_in=100.0),
            support_stirrup_spacing_in=_supp_spacing,
            mid_stirrup_spacing_in=_mid_spacing,
            scale=scale,
            unit=unit or "mm",
        )

    @classmethod
    def from_imperial(
        cls,
        *,
        name: str = "PB-1",
        grid_line_name: str = "A-A",
        spans: Sequence[float] | None = None,
        col_width: float | None = None,
        beam_width: float | None = None,
        beam_depth: float | None = None,
        cover: float | None = None,
        col_extension: float | None = None,
        grid_extension: float | None = None,
        grid_labels: Sequence[str] = (),
        level_text: str = 'ELEV. +10\' - 0"',
        top_bars: Sequence[Rebar] = (),
        bottom_bars: Sequence[Rebar] = (),
        top_extra_bars: Sequence[Rebar] = (),
        stirrup: Stirrup | None = None,
        support_stirrup_spacing: float | None = None,
        mid_stirrup_spacing: float | None = None,
        scale: Any = None,
        unit: Any = None,
    ) -> BeamProfileData:
        """Construct BeamProfileData directly from Imperial parameters (in inches)."""
        _spans = spans if spans is not None else (216.0, 160.0, 120.0, 160.0, 216.0)
        _col_width = col_width if col_width is not None else 18.0
        _beam_width = beam_width if beam_width is not None else 18.0
        _beam_depth = beam_depth if beam_depth is not None else 18.0
        _cover = cover if cover is not None else 1.5
        _col_extension = col_extension if col_extension is not None else 39.0
        _grid_extension = grid_extension if grid_extension is not None else 60.0
        _supp_spacing = support_stirrup_spacing if support_stirrup_spacing is not None else 4.0
        _mid_spacing = mid_stirrup_spacing if mid_stirrup_spacing is not None else 6.0

        return cls(
            name=name,
            grid_line_name=grid_line_name,
            spans_in=tuple(_spans),
            col_width_in=_col_width,
            beam_width_in=_beam_width,
            beam_depth_in=_beam_depth,
            cover_in=_cover,
            col_extension_in=_col_extension,
            grid_extension_in=_grid_extension,
            grid_labels=tuple(grid_labels),
            level_text=level_text,
            top_bars=top_bars,
            bottom_bars=bottom_bars,
            top_extra_bars=top_extra_bars,
            stirrup=stirrup or Stirrup(size="#3", spacing_in=4.0),
            support_stirrup_spacing_in=_supp_spacing,
            mid_stirrup_spacing_in=_mid_spacing,
            scale=scale,
            unit=unit or "in",
        )


@dataclass(frozen=True)
class IsolatedFootingData:
    """All information needed to draw an isolated spread footing (section + plan).

    Attributes
    ----------
    name
        Footing identifier (e.g. ``"F1"``).
    length_in / width_in
        Footing plan dimensions (inches).
    mid_thickness_in / edge_thickness_in
        Sloped-footing thicknesses (inches).
    column_width_in / column_depth_in
        Supported column dimensions (inches).
    column_height_in
        Total column height above the footing top (inches).
    footing_depth_in
        Depth of foundation below ground level (inches).
    plinth_height_in
        Plinth height above ground level (inches).
    cover_in
        Clear cover to the footing reinforcement (inches).
    bar_dia_in
        Footing bar diameter (inches).
    bar_spacing_in
        Footing bar spacing (inches).
    column_bars
        Sequence of :class:`Rebar` for the column longitudinal bars
        that run into the footing.
    column_stirrups
        :class:`Stirrup` description for the column.
    development_length_in
        Development length ``Ld`` shown next to the column bar
        hook into the footing.
    """

    name: str = "F1"
    length_in: float = 64.0
    width_in: float = 64.0
    mid_thickness_in: float = 16.0
    edge_thickness_in: float = 8.0
    column_width_in: float = 14.0
    column_depth_in: float = 14.0
    column_height_in: float = 84.0
    footing_depth_in: float = 60.0
    plinth_height_in: float = 24.0
    cover_in: float = 3.0
    bar_dia_in: float = 0.5
    bar_spacing_in: float = 6.0
    column_bars: Sequence[Rebar] = field(default_factory=tuple)
    column_stirrups: Optional[Stirrup] = None
    bar_size: Optional[str] = None
    development_length_in: float = 24.0
    ledge_in: float = 4.0
    pcc_thickness_in: float = 3.0
    soling_thickness_in: float = 3.0
    soling_material: str = "brick"
    plinth_beam_width_in: float = 0.0
    plinth_beam_depth_in: float = 0.0
    foundation_beam_width_in: float = 0.0
    foundation_beam_depth_in: float = 0.0
    schedule: Sequence[ScheduleRow] = field(default_factory=tuple)
    scale: Any = None
    unit: Any = None

    @property
    def is_metric(self) -> bool:
        """True if the footing dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(self.unit, self.length_in >= 300.0)

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "F2",
        length: float | None = None,
        width: float | None = None,
        mid_thick: float | None = None,
        edge_thick: float | None = None,
        col_width: float | None = None,
        col_depth: float | None = None,
        col_height: float | None = None,
        fd_depth: float | None = None,
        pl_height: float | None = None,
        cover: float | None = None,
        bar_dia: float | None = None,
        bar_spacing: float | None = None,
        ld: float | None = None,
        ledge: float | None = None,
        pcc_thick: float | None = None,
        soling_thick: float | None = None,
        soling_material: str = "brick",
        plinth_beam_w: float | None = None,
        plinth_beam_h: float | None = None,
        found_beam_w: float | None = None,
        found_beam_h: float | None = None,
        column_bars: Sequence[Rebar] = (),
        column_stirrups: Stirrup | None = None,
        bar_size: str | None = None,
        schedule: Sequence[ScheduleRow] = (),
        scale: Any = None,
        unit: Any = None,
    ) -> IsolatedFootingData:
        """Construct IsolatedFootingData directly from SI metric parameters."""
        _length = length if length is not None else 1600.0
        _width = width if width is not None else 1600.0
        _mid_thick = mid_thick if mid_thick is not None else 400.0
        _edge_thick = edge_thick if edge_thick is not None else 200.0
        _col_width = col_width if col_width is not None else 350.0
        _col_depth = col_depth if col_depth is not None else 350.0
        _col_height = col_height if col_height is not None else 2100.0
        _fd_depth = fd_depth if fd_depth is not None else 1500.0
        _pl_height = pl_height if pl_height is not None else 600.0
        _cover = cover if cover is not None else 75.0
        _bar_dia = bar_dia if bar_dia is not None else 12.0
        _bar_spacing = bar_spacing if bar_spacing is not None else 150.0
        _ld = ld if ld is not None else 600.0
        _ledge = ledge if ledge is not None else 100.0
        _pcc_thick = pcc_thick if pcc_thick is not None else 75.0
        _soling_thick = soling_thick if soling_thick is not None else 75.0
        _plinth_beam_w = plinth_beam_w if plinth_beam_w is not None else 230.0
        _plinth_beam_h = plinth_beam_h if plinth_beam_h is not None else 350.0
        _found_beam_w = found_beam_w if found_beam_w is not None else 230.0
        _found_beam_h = found_beam_h if found_beam_h is not None else 300.0

        return cls(
            name=name,
            length_in=_length,
            width_in=_width,
            mid_thickness_in=_mid_thick,
            edge_thickness_in=_edge_thick,
            column_width_in=_col_width,
            column_depth_in=_col_depth,
            column_height_in=_col_height,
            footing_depth_in=_fd_depth,
            plinth_height_in=_pl_height,
            cover_in=_cover,
            bar_dia_in=_bar_dia,
            bar_spacing_in=_bar_spacing,
            development_length_in=_ld,
            ledge_in=_ledge,
            pcc_thickness_in=_pcc_thick,
            soling_thickness_in=_soling_thick,
            soling_material=soling_material,
            plinth_beam_width_in=_plinth_beam_w,
            plinth_beam_depth_in=_plinth_beam_h,
            foundation_beam_width_in=_found_beam_w,
            foundation_beam_depth_in=_found_beam_h,
            column_bars=column_bars,
            column_stirrups=column_stirrups,
            bar_size=bar_size,
            schedule=schedule,
            scale=scale,
            unit=unit or "mm",
        )

    @classmethod
    def from_imperial(
        cls,
        *,
        name: str = "F1",
        length: float | None = None,
        width: float | None = None,
        mid_thick: float | None = None,
        edge_thick: float | None = None,
        col_width: float | None = None,
        col_depth: float | None = None,
        col_height: float | None = None,
        fd_depth: float | None = None,
        pl_height: float | None = None,
        cover: float | None = None,
        bar_dia: float | None = None,
        bar_spacing: float | None = None,
        ld: float | None = None,
        ledge: float | None = None,
        pcc_thick: float | None = None,
        soling_thick: float | None = None,
        soling_material: str = "brick",
        plinth_beam_w: float | None = None,
        plinth_beam_h: float | None = None,
        found_beam_w: float | None = None,
        found_beam_h: float | None = None,
        column_bars: Sequence[Rebar] = (),
        column_stirrups: Stirrup | None = None,
        bar_size: str | None = None,
        schedule: Sequence[ScheduleRow] = (),
        scale: Any = None,
        unit: Any = None,
    ) -> IsolatedFootingData:
        """Construct IsolatedFootingData directly from Imperial parameters (in inches)."""
        _length = length if length is not None else 64.0
        _width = width if width is not None else 64.0
        _mid_thick = mid_thick if mid_thick is not None else 16.0
        _edge_thick = edge_thick if edge_thick is not None else 8.0
        _col_width = col_width if col_width is not None else 14.0
        _col_depth = col_depth if col_depth is not None else 14.0
        _col_height = col_height if col_height is not None else 84.0
        _fd_depth = fd_depth if fd_depth is not None else 60.0
        _pl_height = pl_height if pl_height is not None else 24.0
        _cover = cover if cover is not None else 3.0
        _bar_dia = bar_dia if bar_dia is not None else 0.5
        _bar_spacing = bar_spacing if bar_spacing is not None else 6.0
        _ld = ld if ld is not None else 24.0
        _ledge = ledge if ledge is not None else 4.0
        _pcc_thick = pcc_thick if pcc_thick is not None else 3.0
        _soling_thick = soling_thick if soling_thick is not None else 3.0
        _plinth_beam_w = plinth_beam_w if plinth_beam_w is not None else 0.0
        _plinth_beam_h = plinth_beam_h if plinth_beam_h is not None else 0.0
        _found_beam_w = found_beam_w if found_beam_w is not None else 0.0
        _found_beam_h = found_beam_h if found_beam_h is not None else 0.0

        return cls(
            name=name,
            length_in=_length,
            width_in=_width,
            mid_thickness_in=_mid_thick,
            edge_thickness_in=_edge_thick,
            column_width_in=_col_width,
            column_depth_in=_col_depth,
            column_height_in=_col_height,
            footing_depth_in=_fd_depth,
            plinth_height_in=_pl_height,
            cover_in=_cover,
            bar_dia_in=_bar_dia,
            bar_spacing_in=_bar_spacing,
            development_length_in=_ld,
            ledge_in=_ledge,
            pcc_thickness_in=_pcc_thick,
            soling_thickness_in=_soling_thick,
            soling_material=soling_material,
            plinth_beam_width_in=_plinth_beam_w,
            plinth_beam_depth_in=_plinth_beam_h,
            foundation_beam_width_in=_found_beam_w,
            foundation_beam_depth_in=_found_beam_h,
            column_bars=column_bars,
            column_stirrups=column_stirrups,
            bar_size=bar_size,
            schedule=schedule,
            scale=scale,
            unit=unit or "in",
        )


FootingData = IsolatedFootingData
"""Alias for :class:`IsolatedFootingData`."""


@dataclass(frozen=True)
class CombinedFootingData:
    """All information needed to draw a combined footing (section + plan).

    A combined footing supports two columns on a single concrete pad.

    Attributes
    ----------
    name
        Footing identifier (e.g. ``"CF1"``).
    proj_left_in / proj_right_in
        Cantilever projections on the left of Col 1 center and right of Col 2 center (inches).
    col_spacing_in
        Center-to-center spacing between Column 1 and Column 2 (inches).
    width_in
        Footing pad width (inches).
    thickness_in
        Footing slab thickness (inches).
    col1_width_in / col1_depth_in
        Column 1 dimensions (inches).
    col2_width_in / col2_depth_in
        Column 2 dimensions (inches).
    footing_depth_in
        Depth of foundation below ground level (inches).
    plinth_height_in
        Plinth height above ground level (inches).
    cover_in
        Clear cover to reinforcement (inches).
    bar_dia_in / bar_spacing_in
        Bottom main rebar diameter and spacing (inches).
    top_bar_dia_in / top_bar_spacing_in
        Top main rebar diameter and spacing (inches).
    plinth_beam_width_in / plinth_beam_depth_in
        Plinth beam cross-section dimensions (inches).
    foundation_beam_width_in / foundation_beam_depth_in
        Foundation beam cross-section dimensions (inches).
    column_bars
        Sequence of :class:`Rebar` for column longitudinal steel.
    column_stirrups
        :class:`Stirrup` description for column ties.
    development_length_in
        Development length ``Ld`` shown for rebar anchorage.
    pcc_thickness_in / soling_thickness_in
        Sub-base layer thicknesses (inches).
    """

    name: str = "CF1"
    proj_left_in: float = 60.0
    proj_right_in: float = 48.0
    col_spacing_in: float = 32.0
    width_in: float = 64.0
    thickness_in: float = 16.0
    col1_width_in: float = 14.0
    col1_depth_in: float = 14.0
    col2_width_in: float = 14.0
    col2_depth_in: float = 14.0
    footing_depth_in: float = 60.0
    plinth_height_in: float = 24.0
    pcc_thickness_in: float = 3.0
    soling_thickness_in: float = 3.0
    soling_material: str = "brick"
    cover_in: float = 2.0
    bar_dia_in: float = 0.5
    bar_spacing_in: float = 6.0
    top_bar_dia_in: float | None = None
    top_bar_spacing_in: float | None = None
    plinth_beam_width_in: float = 0.0
    plinth_beam_depth_in: float = 0.0
    foundation_beam_width_in: float = 0.0
    foundation_beam_depth_in: float = 0.0
    column_bars: Sequence[Rebar] = field(default_factory=tuple)
    column_stirrups: Optional[Stirrup] = None
    bar_size: Optional[str] = None
    development_length_in: float = 24.0
    schedule: Sequence[ScheduleRow] = field(default_factory=tuple)
    scale: Any = None
    unit: Any = None

    @property
    def total_length_in(self) -> float:
        """Total length of the combined footing pad."""
        return self.proj_left_in + self.col_spacing_in + self.proj_right_in

    @property
    def is_metric(self) -> bool:
        """True if dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(self.unit, self.total_length_in >= 300.0)

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "CF2",
        proj_left: float | None = None,
        proj_right: float | None = None,
        col_spacing: float | None = None,
        width: float | None = None,
        thickness: float | None = None,
        col1_width: float | None = None,
        col1_depth: float | None = None,
        col2_width: float | None = None,
        col2_depth: float | None = None,
        fd_depth: float | None = None,
        pl_height: float | None = None,
        pcc_thick: float | None = None,
        soling_thick: float | None = None,
        soling_material: str = "brick",
        cover: float | None = None,
        bar_dia: float | None = None,
        bar_spacing: float | None = None,
        top_bar_dia: float | None = None,
        top_bar_spacing: float | None = None,
        plinth_beam_w: float | None = None,
        plinth_beam_h: float | None = None,
        found_beam_w: float | None = None,
        found_beam_h: float | None = None,
        ld: float | None = None,
        column_bars: Sequence[Rebar] = (),
        column_stirrups: Stirrup | None = None,
        schedule: Sequence[ScheduleRow] = (),
        scale: Any = None,
        unit: Any = None,
    ) -> CombinedFootingData:
        """Construct CombinedFootingData directly from SI metric parameters."""
        _proj_left = proj_left if proj_left is not None else 1500.0
        _proj_right = proj_right if proj_right is not None else 1200.0
        _col_spacing = col_spacing if col_spacing is not None else 800.0
        _width = width if width is not None else 1600.0
        _thickness = thickness if thickness is not None else 400.0
        _col1_width = col1_width if col1_width is not None else 350.0
        _col1_depth = col1_depth if col1_depth is not None else 350.0
        _col2_width = col2_width if col2_width is not None else 350.0
        _col2_depth = col2_depth if col2_depth is not None else 350.0
        _fd_depth = fd_depth if fd_depth is not None else 1500.0
        _pl_height = pl_height if pl_height is not None else 600.0
        _pcc_thick = pcc_thick if pcc_thick is not None else 75.0
        _soling_thick = soling_thick if soling_thick is not None else 75.0
        _cover = cover if cover is not None else 50.0
        _bar_dia = bar_dia if bar_dia is not None else 12.0
        _bar_spacing = bar_spacing if bar_spacing is not None else 150.0
        _top_bar_dia = top_bar_dia
        _top_bar_spacing = top_bar_spacing
        _plinth_beam_w = plinth_beam_w if plinth_beam_w is not None else 230.0
        _plinth_beam_h = plinth_beam_h if plinth_beam_h is not None else 350.0
        _found_beam_w = found_beam_w if found_beam_w is not None else 230.0
        _found_beam_h = found_beam_h if found_beam_h is not None else 300.0
        _ld = ld if ld is not None else 600.0

        return cls(
            name=name,
            proj_left_in=_proj_left,
            proj_right_in=_proj_right,
            col_spacing_in=_col_spacing,
            width_in=_width,
            thickness_in=_thickness,
            col1_width_in=_col1_width,
            col1_depth_in=_col1_depth,
            col2_width_in=_col2_width,
            col2_depth_in=_col2_depth,
            footing_depth_in=_fd_depth,
            plinth_height_in=_pl_height,
            pcc_thickness_in=_pcc_thick,
            soling_thickness_in=_soling_thick,
            soling_material=soling_material,
            cover_in=_cover,
            bar_dia_in=_bar_dia,
            bar_spacing_in=_bar_spacing,
            top_bar_dia_in=_top_bar_dia,
            top_bar_spacing_in=_top_bar_spacing,
            plinth_beam_width_in=_plinth_beam_w,
            plinth_beam_depth_in=_plinth_beam_h,
            foundation_beam_width_in=_found_beam_w,
            foundation_beam_depth_in=_found_beam_h,
            development_length_in=_ld,
            column_bars=column_bars,
            column_stirrups=column_stirrups or Stirrup(size="8mm dia", spacing_in=100.0),
            schedule=schedule,
            scale=scale,
            unit=unit or "mm",
        )

    @classmethod
    def from_imperial(
        cls,
        *,
        name: str = "CF1",
        proj_left: float | None = None,
        proj_right: float | None = None,
        col_spacing: float | None = None,
        width: float | None = None,
        thickness: float | None = None,
        col1_width: float | None = None,
        col1_depth: float | None = None,
        col2_width: float | None = None,
        col2_depth: float | None = None,
        fd_depth: float | None = None,
        pl_height: float | None = None,
        pcc_thick: float | None = None,
        soling_thick: float | None = None,
        soling_material: str = "brick",
        cover: float | None = None,
        bar_dia: float | None = None,
        bar_spacing: float | None = None,
        top_bar_dia: float | None = None,
        top_bar_spacing: float | None = None,
        plinth_beam_w: float | None = None,
        plinth_beam_h: float | None = None,
        found_beam_w: float | None = None,
        found_beam_h: float | None = None,
        ld: float | None = None,
        column_bars: Sequence[Rebar] = (),
        column_stirrups: Stirrup | None = None,
        schedule: Sequence[ScheduleRow] = (),
        scale: Any = None,
        unit: Any = None,
    ) -> CombinedFootingData:
        """Construct CombinedFootingData directly from Imperial parameters (in inches)."""
        _proj_left = proj_left if proj_left is not None else 60.0
        _proj_right = proj_right if proj_right is not None else 48.0
        _col_spacing = col_spacing if col_spacing is not None else 32.0
        _width = width if width is not None else 64.0
        _thickness = thickness if thickness is not None else 16.0
        _col1_width = col1_width if col1_width is not None else 14.0
        _col1_depth = col1_depth if col1_depth is not None else 14.0
        _col2_width = col2_width if col2_width is not None else 14.0
        _col2_depth = col2_depth if col2_depth is not None else 14.0
        _fd_depth = fd_depth if fd_depth is not None else 60.0
        _pl_height = pl_height if pl_height is not None else 24.0
        _pcc_thick = pcc_thick if pcc_thick is not None else 3.0
        _soling_thick = soling_thick if soling_thick is not None else 3.0
        _cover = cover if cover is not None else 2.0
        _bar_dia = bar_dia if bar_dia is not None else 0.5
        _bar_spacing = bar_spacing if bar_spacing is not None else 6.0
        _top_bar_dia = top_bar_dia
        _top_bar_spacing = top_bar_spacing
        _plinth_beam_w = plinth_beam_w if plinth_beam_w is not None else 0.0
        _plinth_beam_h = plinth_beam_h if plinth_beam_h is not None else 0.0
        _found_beam_w = found_beam_w if found_beam_w is not None else 0.0
        _found_beam_h = found_beam_h if found_beam_h is not None else 0.0
        _ld = ld if ld is not None else 24.0

        return cls(
            name=name,
            proj_left_in=_proj_left,
            proj_right_in=_proj_right,
            col_spacing_in=_col_spacing,
            width_in=_width,
            thickness_in=_thickness,
            col1_width_in=_col1_width,
            col1_depth_in=_col1_depth,
            col2_width_in=_col2_width,
            col2_depth_in=_col2_depth,
            footing_depth_in=_fd_depth,
            plinth_height_in=_pl_height,
            pcc_thickness_in=_pcc_thick,
            soling_thickness_in=_soling_thick,
            soling_material=soling_material,
            cover_in=_cover,
            bar_dia_in=_bar_dia,
            bar_spacing_in=_bar_spacing,
            top_bar_dia_in=_top_bar_dia,
            top_bar_spacing_in=_top_bar_spacing,
            plinth_beam_width_in=_plinth_beam_w,
            plinth_beam_depth_in=_plinth_beam_h,
            foundation_beam_width_in=_found_beam_w,
            foundation_beam_depth_in=_found_beam_h,
            development_length_in=_ld,
            column_bars=column_bars,
            column_stirrups=column_stirrups or Stirrup(size="#3", spacing_in=6.0),
            schedule=schedule,
            scale=scale,
            unit=unit or "in",
        )


@dataclass(frozen=True)
class ColumnData:
    """All information needed to draw a column (section + elevation).

    Attributes
    ----------
    name
        Column identifier.
    section
        :class:`GeometrySection` description.
    height_in
        Total column height (inches).
    longitudinal_bars
        :class:`Rebar` sequence (corners + sides).
    stirrups
        :class:`Stirrup` description.
    schedule
        Sequence of :class:`ScheduleRow` for the bar schedule.
    """

    name: str = "C1"
    section: GeometrySection = field(default_factory=GeometrySection)
    height_in: float = 120.0
    longitudinal_bars: Sequence[Rebar] = field(default_factory=tuple)
    stirrups: Stirrup = field(default_factory=Stirrup)
    stirrup_zones: Sequence[Stirrup] = field(default_factory=tuple)
    schedule: Sequence[ScheduleRow] = field(default_factory=tuple)
    scale: Any = None
    unit: Any = None
    beam_depth_in: float | None = None
    lo: float | None = None
    so: float | None = None
    s_mid: float | None = None
    s_joint: float | None = None
    l_splice: float | None = None
    splice_class: str = "Class B"

    @property
    def is_metric(self) -> bool:
        """True if the column dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(self.unit, False)


@dataclass(frozen=True)
class ColumnScheduleData:
    """Multi-story column schedule table data and companion typical elevation view.

    Attributes
    ----------
    title : str
        Schedule table title, e.g. ``"COLUMN SCHEDULE"``.
    stories : tuple[str, ...]
        Story identifiers ordered from bottom to top, e.g. ``("STORY 1", "STORY 2")``.
    column_marks : tuple[str, ...]
        Column identifiers/marks, e.g. ``("C1", "C2", "C3", "C4", "C5", "C6")``.
    columns : Mapping[tuple[str, str], ColumnData]
        Dictionary mapping ``(story, column_mark) -> ColumnData``.
    typical_column : ColumnData | None
        Representative column data for drawing typical ground-floor column elevation.
    notes : tuple[str, ...]
        General seismic and detailing notes for columns.
    scale : Any
        Drawing scale for annotations and dimensions.
    unit : Any
        Drawing unit (DrawingUnit.MM or DrawingUnit.IN).
    """

    title: str = "COLUMN SCHEDULE"
    stories: tuple[str, ...] = ()
    column_marks: tuple[str, ...] = ()
    columns: Mapping[tuple[str, str], ColumnData] = field(default_factory=dict)
    typical_column: ColumnData | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    scale: Any = None
    unit: Any = None

    @property
    def is_metric(self) -> bool:
        """True if the column schedule is in SI metric units (mm)."""
        if self.typical_column is not None:
            return self.typical_column.is_metric
        if self.columns:
            first_col = next(iter(self.columns.values()))
            return first_col.is_metric
        return _resolve_unit_is_metric(self.unit, True)


@dataclass(frozen=True)
class StaircaseData:
    """All information needed to draw a staircase (plan + section).

    Attributes
    ----------
    name
        Staircase identifier (e.g. ``"ST1"``).
    flight_width_in
        Width of one flight (inches or mm).
    flight_length_in
        Horizontal length of flight (going length) (inches or mm).
    riser_height_in
        Riser height (inches or mm).
    tread_depth_in
        Tread depth (inches or mm).
    num_risers
        Number of risers in the flight.
    slab_thickness_in
        Waist slab thickness (inches or mm).
    cover_in
        Clear cover to reinforcement (inches or mm).
    bottom_landing_depth_in
        Horizontal length of bottom landing from grid line 1 to 1st riser (inches or mm).
    top_landing_depth_in
        Horizontal length of top landing from last riser to grid line 2 (inches or mm).
    beam_left_width_in / beam_left_depth_in
        Width and depth of the left landing/main beam (inches or mm).
    beam_right_width_in / beam_right_depth_in
        Width and depth of the right landing/main beam (inches or mm).
    main_bar_dia_in / main_bar_spacing_in
        Main reinforcement bar diameter and center-to-center spacing (inches or mm).
    dist_bar_dia_in / dist_bar_spacing_in
        Distribution reinforcement bar diameter and center-to-center spacing (inches or mm).
    nosing_bar_dia_in
        Nosing bar diameter in steps (inches or mm).
    landings
        Number of intermediate landings.
    """

    name: str = "ST1"
    flight_width_in: float = 48.0
    flight_length_in: float = 120.0
    riser_height_in: float = 6.0
    tread_depth_in: float = 12.0
    num_risers: int = 11
    slab_thickness_in: float = 7.5
    cover_in: float = 1.2
    bottom_landing_depth_in: float = 60.0
    top_landing_depth_in: float = 12.0
    beam_left_width_in: float = 9.0
    beam_left_depth_in: float = 14.0
    beam_right_width_in: float = 14.0
    beam_right_depth_in: float = 22.0
    main_bar_dia_in: float = 0.5
    main_bar_spacing_in: float = 5.0
    dist_bar_dia_in: float = 0.375
    dist_bar_spacing_in: float = 6.0
    nosing_bar_dia_in: float = 0.3125
    landings: int = 1
    scale: Any = None
    unit: Any = None

    @property
    def is_metric(self) -> bool:
        """True if dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(
            self.unit,
            self.tread_depth_in >= 100.0 or self.flight_width_in >= 300.0 or self.slab_thickness_in >= 100.0,
        )

    @property
    def waist_thickness_in(self) -> float:
        """Alias for slab_thickness_in."""
        return self.slab_thickness_in

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "ST1",
        flight_width: float | None = None,
        riser: float | None = None,
        tread: float | None = None,
        num_risers: int = 12,
        waist: float | None = None,
        cover: float | None = None,
        bottom_landing: float | None = None,
        top_landing: float | None = None,
        beam_left_w: float | None = None,
        beam_left_h: float | None = None,
        beam_right_w: float | None = None,
        beam_right_h: float | None = None,
        main_bar_dia: float | None = None,
        main_bar_spacing: float | None = None,
        dist_bar_dia: float | None = None,
        dist_bar_spacing: float | None = None,
        nosing_bar_dia: float | None = None,
        landings: int = 1,
    ) -> StaircaseData:
        """Construct StaircaseData directly from SI metric parameters."""
        _flight_width = flight_width if flight_width is not None else 1200.0
        _riser = riser if riser is not None else 150.0
        _tread = tread if tread is not None else 300.0
        _waist = waist if waist is not None else 190.0
        _cover = cover if cover is not None else 30.0
        _bottom_landing = bottom_landing if bottom_landing is not None else 1915.0
        _top_landing = top_landing if top_landing is not None else 285.0
        _beam_left_w = beam_left_w if beam_left_w is not None else 230.0
        _beam_left_h = beam_left_h if beam_left_h is not None else 350.0
        _beam_right_w = beam_right_w if beam_right_w is not None else 350.0
        _beam_right_h = beam_right_h if beam_right_h is not None else 550.0
        _main_bar_dia = main_bar_dia if main_bar_dia is not None else 12.0
        _main_bar_spacing = main_bar_spacing if main_bar_spacing is not None else 125.0
        _dist_bar_dia = dist_bar_dia if dist_bar_dia is not None else 10.0
        _dist_bar_spacing = dist_bar_spacing if dist_bar_spacing is not None else 150.0
        _nosing_bar_dia = nosing_bar_dia if nosing_bar_dia is not None else 8.0

        going_mm = (num_risers - 1) * _tread
        return cls(
            name=name,
            flight_width_in=_flight_width,
            flight_length_in=going_mm,
            riser_height_in=_riser,
            tread_depth_in=_tread,
            num_risers=num_risers,
            slab_thickness_in=_waist,
            cover_in=_cover,
            bottom_landing_depth_in=_bottom_landing,
            top_landing_depth_in=_top_landing,
            beam_left_width_in=_beam_left_w,
            beam_left_depth_in=_beam_left_h,
            beam_right_width_in=_beam_right_w,
            beam_right_depth_in=_beam_right_h,
            main_bar_dia_in=_main_bar_dia,
            main_bar_spacing_in=_main_bar_spacing,
            dist_bar_dia_in=_dist_bar_dia,
            dist_bar_spacing_in=_dist_bar_spacing,
            nosing_bar_dia_in=_nosing_bar_dia,
            landings=landings,
        )

    @classmethod
    def from_imperial(
        cls,
        *,
        name: str = "ST1",
        flight_width: float | None = None,
        riser: float | None = None,
        tread: float | None = None,
        num_risers: int = 11,
        waist: float | None = None,
        cover: float | None = None,
        bottom_landing: float | None = None,
        top_landing: float | None = None,
        beam_left_w: float | None = None,
        beam_left_h: float | None = None,
        beam_right_w: float | None = None,
        beam_right_h: float | None = None,
        main_bar_dia: float | None = None,
        main_bar_spacing: float | None = None,
        dist_bar_dia: float | None = None,
        dist_bar_spacing: float | None = None,
        nosing_bar_dia: float | None = None,
        landings: int = 1,
    ) -> StaircaseData:
        """Construct StaircaseData directly from Imperial parameters (in inches)."""
        _flight_width = flight_width if flight_width is not None else 48.0
        _riser = riser if riser is not None else 6.0
        _tread = tread if tread is not None else 12.0
        _waist = waist if waist is not None else 7.5
        _cover = cover if cover is not None else 1.2
        _bottom_landing = bottom_landing if bottom_landing is not None else 60.0
        _top_landing = top_landing if top_landing is not None else 12.0
        _beam_left_w = beam_left_w if beam_left_w is not None else 9.0
        _beam_left_h = beam_left_h if beam_left_h is not None else 14.0
        _beam_right_w = beam_right_w if beam_right_w is not None else 14.0
        _beam_right_h = beam_right_h if beam_right_h is not None else 22.0
        _main_bar_dia = main_bar_dia if main_bar_dia is not None else 0.5
        _main_bar_spacing = main_bar_spacing if main_bar_spacing is not None else 5.0
        _dist_bar_dia = dist_bar_dia if dist_bar_dia is not None else 0.375
        _dist_bar_spacing = dist_bar_spacing if dist_bar_spacing is not None else 6.0
        _nosing_bar_dia = nosing_bar_dia if nosing_bar_dia is not None else 0.3125

        going = (num_risers - 1) * _tread
        return cls(
            name=name,
            flight_width_in=_flight_width,
            flight_length_in=going,
            riser_height_in=_riser,
            tread_depth_in=_tread,
            num_risers=num_risers,
            slab_thickness_in=_waist,
            cover_in=_cover,
            bottom_landing_depth_in=_bottom_landing,
            top_landing_depth_in=_top_landing,
            beam_left_width_in=_beam_left_w,
            beam_left_depth_in=_beam_left_h,
            beam_right_width_in=_beam_right_w,
            beam_right_depth_in=_beam_right_h,
            main_bar_dia_in=_main_bar_dia,
            main_bar_spacing_in=_main_bar_spacing,
            dist_bar_dia_in=_dist_bar_dia,
            dist_bar_spacing_in=_dist_bar_spacing,
            nosing_bar_dia_in=_nosing_bar_dia,
            landings=landings,
        )


@dataclass(frozen=True)
class SlabData:
    """All information needed to draw a slab (plan + section).

    Attributes
    ----------
    name
        Slab identifier.
    length_in / width_in
        Plan dimensions (inches).
    thickness_in
        Slab thickness (inches).
    cover_in
        Clear cover (inches).
    top_bar / bottom_bar
        :class:`Rebar` descriptions for the top and bottom mats.
    """

    name: str = "S1"
    length_in: float = 240.0
    width_in: float = 120.0
    thickness_in: float = 6.0
    cover_in: float = 0.75
    top_bar: Rebar | None = None
    bottom_bar: Rebar | None = None
    scale: Any = None
    unit: Any = None

    @property
    def is_metric(self) -> bool:
        """True if the slab dimensions are specified in SI metric units (mm)."""
        return _resolve_unit_is_metric(self.unit, self.thickness_in >= 50.0 or self.width_in >= 500.0)


# ---------------------------------------------------------------------------
# General Drawing / Framing Model data classes (plan & elevation without rebar)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameNode:
    """A node / joint in a structural frame or truss.

    Attributes
    ----------
    id
        Node identifier (e.g. ``1``, ``"N1"``).
    x
        X-coordinate in global/frame coordinates.
    y
        Y-coordinate in global/frame coordinates (or elevation Z in 2D frame).
    z
        Z-coordinate (optional, 0.0 for 2D).
    tag
        Optional annotation label.
    """

    id: int | str
    x: float
    y: float
    z: float = 0.0
    tag: str = ""


@dataclass(frozen=True)
class FrameMember:
    """A structural frame member (beam, column, truss chord/web, brace, wall).

    Attributes
    ----------
    id
        Member identifier (e.g. ``"B1"``, ``"C1"``, ``"TC1"``).
    start_node
        Start node ID or (x, y) coordinates.
    end_node
        End node ID or (x, y) coordinates.
    member_type
        Type of member: ``"beam"``, ``"column"``, ``"truss"``, ``"chord"``, ``"strut"``, ``"brace"``, ``"wall"``.
    name
        Display mark (e.g. ``"B-1"``, ``"C-1"``, ``"TC-1"``).
    section_name
        Designation or cross-section string (e.g. ``"300x500"``, ``"W12x26"``, ``"HSS 4x4x1/4"``).
    width_in
        Cross-section width (inches or mm).
    depth_in
        Cross-section depth / height (inches or mm).
    tag
        Optional extra annotation.
    """

    id: int | str
    start_node: int | str | tuple[float, float]
    end_node: int | str | tuple[float, float]
    member_type: str = "beam"
    name: str = ""
    section_name: str = ""
    width_in: float = 12.0
    depth_in: float = 18.0
    tag: str = ""


@dataclass(frozen=True)
class FrameGridLine:
    """A grid axis line with a bubble mark."""

    label: str = "A"
    coord: float = 0.0
    axis: str = "X"  # "X", "Y", or "Z"


@dataclass(frozen=True)
class FrameLevelLine:
    """A floor or story level indicator."""

    label: str = "GL"
    elevation: float = 0.0


@dataclass(frozen=True)
class GeneralFrameData:
    """Comprehensive general arrangement / structural framing model for 2D/3D plans and elevations.

    Draws clean geometric outlines of columns, beams, braces, and trusses with
    grid lines, story levels, dimensions, and member marks — without rebar details.
    """

    name: str = "FRAME-1"
    nodes: Sequence[FrameNode] = field(default_factory=tuple)
    members: Sequence[FrameMember] = field(default_factory=tuple)
    grid_x: Sequence[FrameGridLine] = field(default_factory=tuple)
    grid_y: Sequence[FrameGridLine] = field(default_factory=tuple)
    levels: Sequence[FrameLevelLine] = field(default_factory=tuple)
    title: str = "GENERAL FRAMING ELEVATION"
    view_mode: str = "elevation"  # "elevation", "plan", "truss", "both"
    member_line_mode: str = "outline"  # "outline", "centerline", "both"
    show_dimensions: bool = True
    show_member_tags: bool = True
    show_grid_bubbles: bool = True
    show_level_markers: bool = True
    is_metric: bool = False
    scale: Any = None
    unit: Any = None

    @classmethod
    def from_grid(
        cls,
        *,
        name: str = "FRAME-1",
        bays: Sequence[float] = (240.0, 240.0, 240.0),
        story_heights: Sequence[float] = (144.0, 120.0, 120.0),
        col_width: float = 16.0,
        col_depth: float = 16.0,
        beam_width: float = 12.0,
        beam_depth: float = 20.0,
        grid_labels: Sequence[str] | None = None,
        level_labels: Sequence[str] | None = None,
        braced_bays: Sequence[tuple[int, int]] | None = None,  # list of (bay_idx, story_idx) for X-bracing
        title: str = "BUILDING FRAME ELEVATION",
        view_mode: str = "elevation",
        is_metric: bool | None = None,
        scale: Any = None,
        unit: Any = None,
    ) -> GeneralFrameData:
        """Create a regular multi-bay, multi-story building frame elevation."""
        if is_metric is None:
            is_metric = (len(bays) > 0 and bays[0] >= 1000.0) or (len(story_heights) > 0 and story_heights[0] >= 1000.0)

        # X coords
        x_coords = [0.0]
        for b in bays:
            x_coords.append(x_coords[-1] + b)

        # Y coords (elevations)
        y_coords = [0.0]
        for h in story_heights:
            y_coords.append(y_coords[-1] + h)

        num_x = len(x_coords)
        num_y = len(y_coords)

        # Default labels
        if grid_labels is None:
            grid_labels = [chr(65 + i) if i < 26 else f"G{i+1}" for i in range(num_x)]
        if level_labels is None:
            level_labels = ["GL"] + [f"FL{i}" if i < num_y - 1 else "ROOF" for i in range(1, num_y)]

        # Generate nodes
        nodes = []
        node_map = {}
        node_id = 1
        for j, y in enumerate(y_coords):
            for i, x in enumerate(x_coords):
                n = FrameNode(id=node_id, x=x, y=y)
                nodes.append(n)
                node_map[(i, j)] = node_id
                node_id += 1

        members = []
        mem_id = 1

        # Columns (vertical members between stories)
        for i in range(num_x):
            for j in range(num_y - 1):
                n_bot = node_map[(i, j)]
                n_top = node_map[(i, j + 1)]
                c_name = f"C{i+1}" if num_y <= 2 else f"C{i+1}-{j+1}"
                members.append(
                    FrameMember(
                        id=f"M{mem_id}",
                        start_node=n_bot,
                        end_node=n_top,
                        member_type="column",
                        name=c_name,
                        section_name=f"{int(col_width)}x{int(col_depth)}",
                        width_in=col_width,
                        depth_in=col_depth,
                    )
                )
                mem_id += 1

        # Beams (horizontal members at floor levels j >= 1)
        for j in range(1, num_y):
            for i in range(num_x - 1):
                n_left = node_map[(i, j)]
                n_right = node_map[(i + 1, j)]
                b_name = f"B{i+1}" if num_y <= 2 else f"B{i+1}-{j}"
                members.append(
                    FrameMember(
                        id=f"M{mem_id}",
                        start_node=n_left,
                        end_node=n_right,
                        member_type="beam",
                        name=b_name,
                        section_name=f"{int(beam_width)}x{int(beam_depth)}",
                        width_in=beam_width,
                        depth_in=beam_depth,
                    )
                )
                mem_id += 1

        # Optional Bracing
        if braced_bays:
            for b_idx, s_idx in braced_bays:
                if 0 <= b_idx < num_x - 1 and 0 <= s_idx < num_y - 1:
                    n1 = node_map[(b_idx, s_idx)]
                    n2 = node_map[(b_idx + 1, s_idx + 1)]
                    n3 = node_map[(b_idx + 1, s_idx)]
                    n4 = node_map[(b_idx, s_idx + 1)]
                    brace_w = max(4.0, beam_width * 0.5)
                    members.append(
                        FrameMember(
                            id=f"M{mem_id}",
                            start_node=n1,
                            end_node=n2,
                            member_type="brace",
                            name=f"BR{b_idx+1}-{s_idx+1}A",
                            width_in=brace_w,
                            depth_in=brace_w,
                        )
                    )
                    mem_id += 1
                    members.append(
                        FrameMember(
                            id=f"M{mem_id}",
                            start_node=n3,
                            end_node=n4,
                            member_type="brace",
                            name=f"BR{b_idx+1}-{s_idx+1}B",
                            width_in=brace_w,
                            depth_in=brace_w,
                        )
                    )
                    mem_id += 1

        grids_x = [FrameGridLine(label=grid_labels[i], coord=x, axis="X") for i, x in enumerate(x_coords)]
        levels = [FrameLevelLine(label=level_labels[j], elevation=y) for j, y in enumerate(y_coords)]

        return cls(
            name=name,
            nodes=tuple(nodes),
            members=tuple(members),
            grid_x=tuple(grids_x),
            levels=tuple(levels),
            title=title,
            view_mode=view_mode,
            is_metric=is_metric,
            scale=scale,
            unit=unit,
        )


@dataclass(frozen=True)
class FramingPlanData:
    """Structural floor / roof framing plan view showing beam and column layouts on grid axes."""

    name: str = "FP-1"
    grid_x: Sequence[float] = (240.0, 240.0, 240.0)  # bay widths along X
    grid_y: Sequence[float] = (240.0, 240.0)         # bay depths along Y
    grid_labels_x: Sequence[str] = ()                # "A", "B", "C", "D"
    grid_labels_y: Sequence[str] = ()                # "1", "2", "3"
    col_width_in: float = 16.0
    col_depth_in: float = 16.0
    beam_width_in: float = 12.0
    beam_depth_in: float = 20.0
    title: str = "FLOOR FRAMING PLAN"
    level_name: str = "FIRST FLOOR (EL. +12'-0\")"
    is_metric: bool = False
    secondary_beams: Sequence[tuple[int, int, str]] = field(default_factory=tuple)  # (bay_x, bay_y, "mid_x"|"mid_y")
    scale: Any = None
    unit: Any = None


@dataclass(frozen=True)
class FrameElevationData:
    """2D structural frame elevation along a specific grid line."""

    name: str = "ELEV-1"
    grid_name: str = "GRID A"
    bays: Sequence[float] = (240.0, 240.0, 240.0)
    story_heights: Sequence[float] = (144.0, 120.0, 120.0)
    col_width_in: float = 16.0
    col_depth_in: float = 16.0
    beam_width_in: float = 12.0
    beam_depth_in: float = 20.0
    grid_labels: Sequence[str] = ()
    level_labels: Sequence[str] = ()
    braced_bays: Sequence[tuple[int, int]] = field(default_factory=tuple)
    title: str = "FRAME ELEVATION - GRID A"
    is_metric: bool = False
    scale: Any = None
    unit: Any = None


@dataclass(frozen=True)
class TrussData:
    """Steel or timber roof/bridge truss general outline view."""

    name: str = "TRUSS-1"
    span_in: float = 480.0
    height_in: float = 96.0
    panels: int = 6
    truss_type: str = "pratt"  # "pratt", "howe", "warren", "pitched", "fink"
    chord_width_in: float = 6.0
    chord_depth_in: float = 6.0
    web_width_in: float = 4.0
    web_depth_in: float = 4.0
    title: str = "ROOF TRUSS OUTLINE & ELEVATION"
    is_metric: bool = False

    @classmethod
    def from_span(
        cls,
        *,
        name: str = "TRUSS-1",
        span: float = 480.0,
        height: float = 96.0,
        panels: int = 6,
        truss_type: str = "pratt",
        chord_depth: float | None = None,
        web_depth: float | None = None,
        is_metric: bool | None = None,
        title: str | None = None,
    ) -> TrussData:
        """Construct TrussData with automatic dimension defaults."""
        if is_metric is None:
            is_metric = span >= 2000.0 or height >= 1000.0
        cd = chord_depth if chord_depth is not None else (150.0 if is_metric else 6.0)
        wd = web_depth if web_depth is not None else (100.0 if is_metric else 4.0)
        return cls(
            name=name,
            span_in=span,
            height_in=height,
            panels=panels,
            truss_type=truss_type,
            chord_width_in=cd,
            chord_depth_in=cd,
            web_width_in=wd,
            web_depth_in=wd,
            title=title or f"{truss_type.upper()} TRUSS ELEVATION",
            is_metric=is_metric,
        )

    @classmethod
    def pratt(
        cls,
        *,
        span_in: float = 480.0,
        height_in: float = 96.0,
        panels: int = 6,
        title: str = "PRATT ROOF TRUSS",
        chord_depth: float | None = None,
        web_depth: float | None = None,
        is_metric: bool | None = None,
    ) -> TrussData:
        return cls.from_span(
            span=span_in,
            height=height_in,
            panels=panels,
            truss_type="pratt",
            title=title,
            chord_depth=chord_depth,
            web_depth=web_depth,
            is_metric=is_metric,
        )

    @classmethod
    def warren(
        cls,
        *,
        span_in: float = 480.0,
        height_in: float = 96.0,
        panels: int = 6,
        title: str = "WARREN TRUSS",
        chord_depth: float | None = None,
        web_depth: float | None = None,
        is_metric: bool | None = None,
    ) -> TrussData:
        return cls.from_span(
            span=span_in,
            height=height_in,
            panels=panels,
            truss_type="warren",
            title=title,
            chord_depth=chord_depth,
            web_depth=web_depth,
            is_metric=is_metric,
        )

    @classmethod
    def howe(
        cls,
        *,
        span_in: float = 480.0,
        height_in: float = 96.0,
        panels: int = 6,
        title: str = "HOWE TRUSS",
        chord_depth: float | None = None,
        web_depth: float | None = None,
        is_metric: bool | None = None,
    ) -> TrussData:
        return cls.from_span(
            span=span_in,
            height=height_in,
            panels=panels,
            truss_type="howe",
            title=title,
            chord_depth=chord_depth,
            web_depth=web_depth,
            is_metric=is_metric,
        )

    @classmethod
    def pitched(
        cls,
        *,
        span_in: float = 480.0,
        height_in: float = 120.0,
        panels: int = 6,
        title: str = "PITCHED ROOF TRUSS",
        chord_depth: float | None = None,
        web_depth: float | None = None,
        is_metric: bool | None = None,
    ) -> TrussData:
        return cls.from_span(
            span=span_in,
            height=height_in,
            panels=panels,
            truss_type="pitched",
            title=title,
            chord_depth=chord_depth,
            web_depth=web_depth,
            is_metric=is_metric,
        )


# ---------------------------------------------------------------------------
# Member-type enum (used by adapters / dispatch)
# ---------------------------------------------------------------------------


class MemberType(str, Enum):
    """The structural-member type a :class:`BeamData` / :class:`FootingData` / ... carries."""

    BEAM = "beam"
    BEAM_PROFILE = "beam_profile"
    FOOTING = "footing"
    COMBINED_FOOTING = "combined_footing"
    COLUMN = "column"
    STAIRCASE = "staircase"
    SLAB = "slab"
    GENERAL_FRAME = "general_frame"
    FRAMING_PLAN = "framing_plan"
    FRAME_ELEVATION = "frame_elevation"
    TRUSS = "truss"


__all__ = [
    "Point",
    "Rebar",
    "Stirrup",
    "ScheduleRow",
    "ScheduleTableData",
    "GeometrySection",
    "BeamData",
    "BeamProfileSpan",
    "BeamProfileData",
    "IsolatedFootingData",
    "FootingData",
    "CombinedFootingData",
    "ColumnData",
    "ColumnScheduleData",
    "StaircaseData",
    "SlabData",
    "FrameNode",
    "FrameMember",
    "FrameGridLine",
    "FrameLevelLine",
    "GeneralFrameData",
    "FramingPlanData",
    "FrameElevationData",
    "TrussData",
    "MemberType",
]