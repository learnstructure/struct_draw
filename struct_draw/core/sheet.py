"""struct_draw.core.sheet — Sheet, SheetSet, and PaperSize.

Declarative sheet composition. The :class:`Sheet` dataclass
describes the paper size, the title-block contents, the viewport
layout, and the sheet-wide annotations. Backends translate these
into the format-specific layout tabs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator, Mapping


class PaperSize(str, Enum):
    """Standard paper sizes for structural drawings (US customary)."""

    ANSI_A = "ANSI_A"    # 8.5 x 11
    ANSI_B = "ANSI_B"    # 11 x 17
    ANSI_C = "ANSI_C"    # 17 x 22
    ANSI_D = "ANSI_D"    # 22 x 34
    ANSI_E = "ANSI_E"    # 34 x 44
    ARCH_C = "ARCH_C"    # 18 x 24
    ARCH_D = "ARCH_D"    # 24 x 36
    ARCH_E = "ARCH_E"    # 36 x 48
    ISO_A1 = "ISO_A1"    # 594 x 841 mm
    ISO_A2 = "ISO_A2"    # 420 x 594 mm
    ISO_A3 = "ISO_A3"    # 297 x 420 mm
    CUSTOM = "CUSTOM"


PAPER_DIMENSIONS_INCHES: dict[PaperSize, tuple[float, float]] = {
    PaperSize.ANSI_A: (8.5, 11.0),
    PaperSize.ANSI_B: (11.0, 17.0),
    PaperSize.ANSI_C: (17.0, 22.0),
    PaperSize.ANSI_D: (22.0, 34.0),
    PaperSize.ANSI_E: (34.0, 44.0),
    PaperSize.ARCH_C: (18.0, 24.0),
    PaperSize.ARCH_D: (24.0, 36.0),
    PaperSize.ARCH_E: (36.0, 48.0),
    PaperSize.ISO_A1: (23.39, 33.11),
    PaperSize.ISO_A2: (16.54, 23.39),
    PaperSize.ISO_A3: (11.69, 16.54),
}


@dataclass(frozen=True)
class Sheet:
    """One drawing sheet.

    Attributes
    ----------
    name
        Sheet identifier shown in the title block.
    paper_size
        :class:`PaperSize` enum value.
    width_in / height_in
        Custom dimensions (used when ``paper_size=CUSTOM``).
    layout
        The :class:`struct_draw.core.viewport.ViewportLayout` for
        this sheet (optional; default layout used when ``None``).
    title_block
        Free-form title-block contents (project, client, date,
        drawing number, revision, scale, sheet number, etc.).
    annotations
        Sheet-wide notes (general notes, abbreviations list,
        legend, etc.).
    """

    name: str
    paper_size: PaperSize = PaperSize.ANSI_B
    width_in: float | None = None
    height_in: float | None = None
    layout: Any | None = None
    title_block: Mapping[str, str] = field(default_factory=dict)
    annotations: tuple[str, ...] = field(default_factory=tuple)

    def dimensions_inches(self) -> tuple[float, float]:
        if self.paper_size is PaperSize.CUSTOM:
            if self.width_in is None or self.height_in is None:
                raise ValueError(
                    "CUSTOM paper_size requires explicit width_in and height_in."
                )
            return (self.width_in, self.height_in)
        return PAPER_DIMENSIONS_INCHES[self.paper_size]


@dataclass
class SheetSet:
    """An ordered collection of :class:`Sheet` objects."""

    sheets: list[Sheet] = field(default_factory=list)

    def add(self, sheet: Sheet) -> None:
        if not sheet.name:
            raise ValueError("Sheet name must be non-empty.")
        self.sheets.append(sheet)

    def by_name(self, name: str) -> Sheet | None:
        return next((s for s in self.sheets if s.name == name), None)

    def __iter__(self) -> Iterator[Sheet]:
        return iter(self.sheets)

    def __len__(self) -> int:
        return len(self.sheets)


__all__ = [
    "PaperSize",
    "PAPER_DIMENSIONS_INCHES",
    "Sheet",
    "SheetSet",
]