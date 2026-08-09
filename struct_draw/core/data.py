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
from typing import Sequence


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


Point = tuple[float, float]


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


@dataclass(frozen=True)
class ScheduleRow:
    """One row in the bar schedule (a ``ScheduleRow`` table line)."""

    mark: str
    size: str
    quantity: int
    length_in: float
    remarks: str = ""


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

    @property
    def is_metric(self) -> bool:
        """True if dimensions are specified in SI metric units (mm)."""
        return self.beam_depth_in >= 100.0 or (len(self.spans_in) > 0 and self.spans_in[0] >= 300.0)

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "PB-1",
        grid_line_name: str = "A-A",
        spans_mm: Sequence[float] = (5500.0, 4000.0, 3000.0, 4000.0, 5500.0),
        col_width_mm: float = 450.0,
        beam_width_mm: float = 450.0,
        beam_depth_mm: float = 450.0,
        cover_mm: float = 40.0,
        col_extension_mm: float = 975.0,
        grid_extension_mm: float = 1500.0,
        grid_labels: Sequence[str] = (),
        level_text: str = "PL+3.0 m",
        top_bars: Sequence[Rebar] = (),
        bottom_bars: Sequence[Rebar] = (),
        top_extra_bars: Sequence[Rebar] = (),
        stirrup: Stirrup | None = None,
        support_stirrup_spacing_mm: float = 100.0,
        mid_stirrup_spacing_mm: float = 150.0,
    ) -> BeamProfileData:
        """Construct BeamProfileData directly from SI metric parameters (in mm)."""
        return cls(
            name=name,
            grid_line_name=grid_line_name,
            spans_in=tuple(spans_mm),
            col_width_in=col_width_mm,
            beam_width_in=beam_width_mm,
            beam_depth_in=beam_depth_mm,
            cover_in=cover_mm,
            col_extension_in=col_extension_mm,
            grid_extension_in=grid_extension_mm,
            grid_labels=tuple(grid_labels),
            level_text=level_text,
            top_bars=top_bars,
            bottom_bars=bottom_bars,
            top_extra_bars=top_extra_bars,
            stirrup=stirrup or Stirrup(size="10mm dia", spacing_in=100.0),
            support_stirrup_spacing_in=support_stirrup_spacing_mm,
            mid_stirrup_spacing_in=mid_stirrup_spacing_mm,
        )


@dataclass(frozen=True)
class FootingData:
    """All information needed to draw a spread footing (section + plan).

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
    column_stirrups: Stirrup = field(default_factory=Stirrup)
    development_length_in: float = 24.0
    ledge_in: float = 4.0
    pcc_thickness_in: float = 3.0
    soling_thickness_in: float = 3.0
    soling_material: str = "brick"
    plinth_beam_width_in: float = 0.0
    plinth_beam_depth_in: float = 0.0
    foundation_beam_width_in: float = 0.0
    foundation_beam_depth_in: float = 0.0

    @property
    def is_metric(self) -> bool:
        """True if the footing dimensions are specified in SI metric units (mm)."""
        return self.length_in >= 300.0

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "F2",
        length_mm: float = 1600.0,
        width_mm: float = 1600.0,
        mid_thick_mm: float = 400.0,
        edge_thick_mm: float = 200.0,
        col_width_mm: float = 350.0,
        col_depth_mm: float = 350.0,
        col_height_mm: float = 2100.0,
        fd_depth_mm: float = 1500.0,
        pl_height_mm: float = 600.0,
        cover_mm: float = 75.0,
        bar_dia_mm: float = 12.0,
        bar_spacing_mm: float = 150.0,
        ld_mm: float = 600.0,
        ledge_mm: float = 100.0,
        pcc_thick_mm: float = 75.0,
        soling_thick_mm: float = 75.0,
        soling_material: str = "brick",
        plinth_beam_w_mm: float = 230.0,
        plinth_beam_h_mm: float = 350.0,
        found_beam_w_mm: float = 230.0,
        found_beam_h_mm: float = 300.0,
        column_bars: Sequence[Rebar] = (),
        column_stirrups: Stirrup | None = None,
    ) -> FootingData:
        """Construct FootingData directly from SI metric parameters (in mm)."""
        return cls(
            name=name,
            length_in=length_mm,
            width_in=width_mm,
            mid_thickness_in=mid_thick_mm,
            edge_thickness_in=edge_thick_mm,
            column_width_in=col_width_mm,
            column_depth_in=col_depth_mm,
            column_height_in=col_height_mm,
            footing_depth_in=fd_depth_mm,
            plinth_height_in=pl_height_mm,
            cover_in=cover_mm,
            bar_dia_in=bar_dia_mm,
            bar_spacing_in=bar_spacing_mm,
            development_length_in=ld_mm,
            ledge_in=ledge_mm,
            pcc_thickness_in=pcc_thick_mm,
            soling_thickness_in=soling_thick_mm,
            soling_material=soling_material,
            plinth_beam_width_in=plinth_beam_w_mm,
            plinth_beam_depth_in=plinth_beam_h_mm,
            foundation_beam_width_in=found_beam_w_mm,
            foundation_beam_depth_in=found_beam_h_mm,
            column_bars=column_bars,
            column_stirrups=column_stirrups or Stirrup(size="8mm dia", spacing_in=100.0),
        )


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
    column_stirrups: Stirrup = field(default_factory=Stirrup)
    development_length_in: float = 24.0

    @property
    def total_length_in(self) -> float:
        """Total length of the combined footing pad."""
        return self.proj_left_in + self.col_spacing_in + self.proj_right_in

    @property
    def is_metric(self) -> bool:
        """True if dimensions are specified in SI metric units (mm)."""
        return self.total_length_in >= 300.0

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "CF2",
        proj_left_mm: float = 1500.0,
        proj_right_mm: float = 1200.0,
        col_spacing_mm: float = 800.0,
        width_mm: float = 1600.0,
        thickness_mm: float = 400.0,
        col1_width_mm: float = 350.0,
        col1_depth_mm: float = 350.0,
        col2_width_mm: float = 350.0,
        col2_depth_mm: float = 350.0,
        fd_depth_mm: float = 1500.0,
        pl_height_mm: float = 600.0,
        pcc_thick_mm: float = 75.0,
        soling_thick_mm: float = 75.0,
        soling_material: str = "brick",
        cover_mm: float = 50.0,
        bar_dia_mm: float = 12.0,
        bar_spacing_mm: float = 150.0,
        top_bar_dia_mm: float | None = None,
        top_bar_spacing_mm: float | None = None,
        plinth_beam_w_mm: float = 230.0,
        plinth_beam_h_mm: float = 350.0,
        found_beam_w_mm: float = 230.0,
        found_beam_h_mm: float = 300.0,
        ld_mm: float = 600.0,
        column_bars: Sequence[Rebar] = (),
        column_stirrups: Stirrup | None = None,
    ) -> CombinedFootingData:
        """Construct CombinedFootingData directly from SI metric parameters (in mm)."""
        return cls(
            name=name,
            proj_left_in=proj_left_mm,
            proj_right_in=proj_right_mm,
            col_spacing_in=col_spacing_mm,
            width_in=width_mm,
            thickness_in=thickness_mm,
            col1_width_in=col1_width_mm,
            col1_depth_in=col1_depth_mm,
            col2_width_in=col2_width_mm,
            col2_depth_in=col2_depth_mm,
            footing_depth_in=fd_depth_mm,
            plinth_height_in=pl_height_mm,
            pcc_thickness_in=pcc_thick_mm,
            soling_thickness_in=soling_thick_mm,
            soling_material=soling_material,
            cover_in=cover_mm,
            bar_dia_in=bar_dia_mm,
            bar_spacing_in=bar_spacing_mm,
            top_bar_dia_in=top_bar_dia_mm,
            top_bar_spacing_in=top_bar_spacing_mm,
            plinth_beam_width_in=plinth_beam_w_mm,
            plinth_beam_depth_in=plinth_beam_h_mm,
            foundation_beam_width_in=found_beam_w_mm,
            foundation_beam_depth_in=found_beam_h_mm,
            development_length_in=ld_mm,
            column_bars=column_bars,
            column_stirrups=column_stirrups or Stirrup(size="8mm dia", spacing_in=100.0),
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
    schedule: Sequence[ScheduleRow] = field(default_factory=tuple)


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

    @property
    def is_metric(self) -> bool:
        """True if dimensions are specified in SI metric units (mm)."""
        return self.tread_depth_in >= 100.0 or self.flight_width_in >= 300.0 or self.slab_thickness_in >= 100.0

    @property
    def waist_thickness_in(self) -> float:
        """Alias for slab_thickness_in."""
        return self.slab_thickness_in

    @classmethod
    def from_metric(
        cls,
        *,
        name: str = "ST1",
        flight_width_mm: float = 1200.0,
        riser_mm: float = 150.0,
        tread_mm: float = 300.0,
        num_risers: int = 12,
        waist_mm: float = 190.0,
        cover_mm: float = 30.0,
        bottom_landing_mm: float = 1915.0,
        top_landing_mm: float = 285.0,
        beam_left_w_mm: float = 230.0,
        beam_left_h_mm: float = 350.0,
        beam_right_w_mm: float = 350.0,
        beam_right_h_mm: float = 550.0,
        main_bar_dia_mm: float = 12.0,
        main_bar_spacing_mm: float = 125.0,
        dist_bar_dia_mm: float = 10.0,
        dist_bar_spacing_mm: float = 150.0,
        nosing_bar_dia_mm: float = 8.0,
        landings: int = 1,
    ) -> StaircaseData:
        """Construct StaircaseData directly from SI metric parameters (in mm)."""
        going_mm = (num_risers - 1) * tread_mm
        return cls(
            name=name,
            flight_width_in=flight_width_mm,
            flight_length_in=going_mm,
            riser_height_in=riser_mm,
            tread_depth_in=tread_mm,
            num_risers=num_risers,
            slab_thickness_in=waist_mm,
            cover_in=cover_mm,
            bottom_landing_depth_in=bottom_landing_mm,
            top_landing_depth_in=top_landing_mm,
            beam_left_width_in=beam_left_w_mm,
            beam_left_depth_in=beam_left_h_mm,
            beam_right_width_in=beam_right_w_mm,
            beam_right_depth_in=beam_right_h_mm,
            main_bar_dia_in=main_bar_dia_mm,
            main_bar_spacing_in=main_bar_spacing_mm,
            dist_bar_dia_in=dist_bar_dia_mm,
            dist_bar_spacing_in=dist_bar_spacing_mm,
            nosing_bar_dia_in=nosing_bar_dia_mm,
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


__all__ = [
    "Point",
    "Rebar",
    "Stirrup",
    "ScheduleRow",
    "GeometrySection",
    "BeamData",
    "BeamProfileSpan",
    "BeamProfileData",
    "FootingData",
    "CombinedFootingData",
    "ColumnData",
    "StaircaseData",
    "SlabData",
    "MemberType",
]