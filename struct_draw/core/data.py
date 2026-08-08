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
        Staircase identifier.
    flight_width_in
        Width of one flight (inches).
    flight_length_in
        Horizontal length of one flight (inches).
    riser_height_in
        Riser height (inches).
    tread_depth_in
        Tread depth (inches).
    slab_thickness_in
        Waist slab thickness (inches).
    landings
        Number of intermediate landings.
    """

    name: str = "ST1"
    flight_width_in: float = 48.0
    flight_length_in: float = 120.0
    riser_height_in: float = 7.0
    tread_depth_in: float = 11.0
    slab_thickness_in: float = 6.0
    landings: int = 1


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
    FOOTING = "footing"
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
    "FootingData",
    "ColumnData",
    "StaircaseData",
    "SlabData",
    "MemberType",
]