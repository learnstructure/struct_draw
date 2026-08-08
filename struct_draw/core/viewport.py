"""struct_draw.core.viewport — Viewport dataclasses and the default layout.

A :class:`Viewport` describes a rectangular window in paper space
that holds one view. The default layout places a section in the
upper-left, an elevation in the upper-right, the bar schedule in
the lower band, and the title block in the lower-right.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class ViewKind(str, Enum):
    """The kind of view a :class:`Viewport` displays.

    Used by sheet composers to route element functions to the
    right viewport (and by element functions to pick the right
    drawing style for the view).
    """

    PLAN = "plan"
    ELEVATION = "elevation"
    SECTION = "section"
    DETAIL = "detail"
    SCHEDULE = "schedule"
    TITLE_BLOCK = "title_block"
    GENERAL = "general"


@dataclass(frozen=True)
class Viewport:
    """A rectangular window in paper space holding one view.

    Attributes
    ----------
    name
        Unique viewport name (used by sheet composers).
    view
        Which kind of view this viewport displays.
    bounds
        ``(x_min, y_min, x_max, y_max)`` in paper-space units
        (typically inches).
    scale
        Drawing-units-per-paper-unit. For example, a scale of
        ``0.5`` means 1 paper inch renders 0.5 model inches
        (i.e., a 2x larger drawing than 1:1).
    rotation
        Rotation angle in degrees, counter-clockwise.
    """

    name: str
    view: ViewKind
    bounds: tuple[float, float, float, float]
    scale: float = 1.0
    rotation: float = 0.0


@dataclass
class ViewportLayout:
    """An ordered collection of :class:`Viewport` objects for one sheet."""

    viewports: list[Viewport] = field(default_factory=list)

    def add(self, viewport: Viewport) -> None:
        if not viewport.name:
            raise ValueError("Viewport name must be non-empty.")
        self.viewports.append(viewport)

    def by_view(self, view: ViewKind) -> list[Viewport]:
        return [vp for vp in self.viewports if vp.view is view]

    def __iter__(self) -> Iterator[Viewport]:
        return iter(self.viewports)

    def __len__(self) -> int:
        return len(self.viewports)


def default_layout(
    *,
    sheet_width: float = 36.0,
    sheet_height: float = 24.0,
) -> ViewportLayout:
    """Return a standard structural-drawing layout for an ANSI D sheet.

    The default places:
      - a primary section viewport in the upper-left quadrant,
      - a longitudinal elevation viewport in the upper-right,
      - a bar-schedule / notes block in the lower band,
      - a title block in the lower-right.
    """
    layout = ViewportLayout()

    layout.add(
        Viewport(
            name="SECTION_PRIMARY",
            view=ViewKind.SECTION,
            bounds=(1.0, sheet_height - 16.0, 18.0, sheet_height - 1.0),
            scale=1.0,
        )
    )
    layout.add(
        Viewport(
            name="ELEVATION_PRIMARY",
            view=ViewKind.ELEVATION,
            bounds=(19.0, sheet_height - 16.0, sheet_width - 1.0, sheet_height - 1.0),
            scale=1.0,
        )
    )
    layout.add(
        Viewport(
            name="SCHEDULE",
            view=ViewKind.SCHEDULE,
            bounds=(1.0, 1.0, 26.0, 7.0),
            scale=1.0,
        )
    )
    layout.add(
        Viewport(
            name="TITLE_BLOCK",
            view=ViewKind.TITLE_BLOCK,
            bounds=(27.0, 1.0, sheet_width - 1.0, 7.0),
            scale=1.0,
        )
    )
    return layout


__all__ = [
    "ViewKind",
    "Viewport",
    "ViewportLayout",
    "default_layout",
]