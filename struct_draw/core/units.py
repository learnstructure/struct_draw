"""struct_draw.core.units — Unit systems, drawing units, and print view scales.

Connects struct_draw with struct_core.units and establishes standard drafting
print sizes (2.0 mm dimensions, 3.0 mm text, 5.0 mm titles on paper).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Optional, Tuple, Union


class DrawingUnit(str, Enum):
    """CAD Modelspace drawing units."""

    MM = "mm"
    CM = "cm"
    M = "m"
    IN = "in"
    FT = "ft"

    @property
    def is_metric(self) -> bool:
        return self in (DrawingUnit.MM, DrawingUnit.CM, DrawingUnit.M)

    @property
    def scale_to_mm(self) -> float:
        """Conversion factor: multiplying drawing unit value by this gives millimeters."""
        if self == DrawingUnit.MM:
            return 1.0
        if self == DrawingUnit.CM:
            return 10.0
        if self == DrawingUnit.M:
            return 1000.0
        if self == DrawingUnit.IN:
            return 25.4
        if self == DrawingUnit.FT:
            return 304.8
        return 1.0

    def format_dimension(self, val: float, precision: Optional[int] = None) -> str:
        """Format dimension text for this drawing unit."""
        if self == DrawingUnit.FT:
            if precision is not None:
                return f"{val:.{precision}f}'"
            feet = int(val)
            inches = (val - feet) * 12.0
            if abs(inches - round(inches)) < 1e-3:
                inch_int = int(round(inches))
                if inch_int == 12:
                    feet += 1
                    inch_int = 0
                return f"{feet}'-{inch_int}\""
            else:
                inch_str = f"{inches:.2f}".rstrip("0").rstrip(".")
                return f"{feet}'-{inch_str}\""

        if precision is None:
            if abs(val - round(val)) < 1e-4:
                formatted_num = f"{int(round(val))}"
            else:
                formatted_num = f"{val:.2f}".rstrip("0").rstrip(".")
        else:
            formatted_num = f"{val:.{precision}f}"

        if self == DrawingUnit.IN:
            return f'{formatted_num}"'
        elif self == DrawingUnit.M:
            return f"{formatted_num}m"
        else:  # MM or CM
            return formatted_num

    @classmethod
    def from_str(cls, s: Union[str, DrawingUnit]) -> DrawingUnit:
        """Resolve a DrawingUnit from string or DrawingUnit instance."""
        if isinstance(s, cls):
            return s
        raw_val = getattr(s, "value", str(s))
        clean = str(raw_val).strip().lower()
        if "." in clean:
            clean = clean.split(".")[-1]
        if clean in ("mm", "millimeter", "millimeters"):
            return cls.MM
        elif clean in ("cm", "centimeter", "centimeters"):
            return cls.CM
        elif clean in ("m", "meter", "meters", "metre", "metres"):
            return cls.M
        elif clean in ("in", "inch", "inches", '"'):
            return cls.IN
        elif clean in ("ft", "foot", "feet", "'"):
            return cls.FT
        elif "metric" in clean or "si" in clean:
            return cls.MM
        elif "imperial" in clean or "customary" in clean or "us" in clean:
            return cls.IN
        return cls.MM



@dataclass(frozen=True)
class DrawingScale:
    """Represents CAD viewport / drawing print scale.

    Parameters
    ----------
    ratio : float
        Scale factor denominator S where Modelspace = PaperSpace * S.
        For example:
        - 1:50  metric -> ratio = 50.0
        - 1:100 metric -> ratio = 100.0
        - 1:20  metric -> ratio = 20.0
        - 1/4" = 1'-0" imperial (1:48) -> ratio = 48.0
        - 1/8" = 1'-0" imperial (1:96) -> ratio = 96.0
        - 1" = 1'-0"   imperial (1:12) -> ratio = 12.0
    name : str
        Human-readable representation (e.g. "1:50", "1/4\" = 1'-0\"").
    is_metric : bool
        Whether this scale is metric or US customary.
    """

    ratio: float
    name: str
    is_metric: bool = True

    @classmethod
    def metric(cls, denominator: float, name: Optional[str] = None) -> DrawingScale:
        """Create a metric scale (e.g. DrawingScale.metric(50) for 1:50)."""
        d = float(denominator)
        n = name or (f"1:{int(d)}" if d.is_integer() else f"1:{d:.1f}")
        return cls(ratio=d, name=n, is_metric=True)

    @classmethod
    def imperial(cls, ratio_or_name: Union[float, str], name: Optional[str] = None) -> DrawingScale:
        """Create an imperial scale from ratio or string representation."""
        if isinstance(ratio_or_name, (int, float)):
            r = float(ratio_or_name)
            n = name or f"1:{int(r)}"
            return cls(ratio=r, name=n, is_metric=False)

        s = str(ratio_or_name).strip()
        # Match e.g. 1/4" = 1'-0", 1/8"=1'-0", 1"=1'-0", 3/4" = 1'-0"
        m = re.match(r'^(\d+)(?:/(\d+))?\s*"\s*=\s*1\'-0"?$', s)
        if m:
            num = float(m.group(1))
            den = float(m.group(2)) if m.group(2) else 1.0
            fraction_in = num / den
            # 1 foot = 12 inches. Scale ratio = 12 / fraction_in
            r = 12.0 / fraction_in
            return cls(ratio=r, name=name or s, is_metric=False)

        # Check for ratio like 1:48 or 48
        if ":" in s:
            parts = s.split(":")
            r = float(parts[1]) / float(parts[0])
            return cls(ratio=r, name=name or s, is_metric=False)

        try:
            r = float(s)
            return cls(ratio=r, name=name or f"1:{int(r)}", is_metric=False)
        except ValueError:
            return cls(ratio=48.0, name=s, is_metric=False)

    @classmethod
    def from_str(cls, s: Union[str, DrawingScale], is_metric: Optional[bool] = None) -> DrawingScale:
        """Parse standard scale strings like '1:50', '1:20', '1/4\"=1'-0\"'."""
        if isinstance(s, cls):
            return s
        clean = str(s).strip()
        if clean.lower() == "full" or clean == "1:1":
            return cls(ratio=1.0, name="1:1", is_metric=True if is_metric is None else is_metric)
        if ":" in clean and not ("=" in clean or '"' in clean):
            parts = clean.split(":")
            r = float(parts[1]) / float(parts[0])
            metric = is_metric if is_metric is not None else True
            return cls(ratio=r, name=clean, is_metric=metric)
        if '"' in clean or "'" in clean or "=" in clean:
            return cls.imperial(clean)
        try:
            r = float(clean)
            metric = is_metric if is_metric is not None else (r in (10, 20, 25, 30, 50, 100, 200, 500))
            return cls(ratio=r, name=f"1:{int(r)}" if r.is_integer() else f"1:{r}", is_metric=metric)
        except ValueError:
            return cls.metric(50.0, "1:50") if (is_metric is None or is_metric) else cls.imperial(48.0, '1/4" = 1\'-0"')


# Standard View Scale Presets
SCALE_1_100 = DrawingScale.metric(100.0, "1:100")
SCALE_1_50 = DrawingScale.metric(50.0, "1:50")
SCALE_1_30 = DrawingScale.metric(30.0, "1:30")
SCALE_1_25 = DrawingScale.metric(25.0, "1:25")
SCALE_1_20 = DrawingScale.metric(20.0, "1:20")
SCALE_1_10 = DrawingScale.metric(10.0, "1:10")

SCALE_1_8_IN = DrawingScale.imperial('1/8" = 1\'-0"')   # 1:96
SCALE_1_4_IN = DrawingScale.imperial('1/4" = 1\'-0"')   # 1:48
SCALE_1_2_IN = DrawingScale.imperial('1/2" = 1\'-0"')   # 1:24
SCALE_3_4_IN = DrawingScale.imperial('3/4" = 1\'-0"')   # 1:16
SCALE_1_IN = DrawingScale.imperial('1" = 1\'-0"')       # 1:12
SCALE_3_IN = DrawingScale.imperial('3" = 1\'-0"')       # 1:4



def drawing_unit_from_core(
    project_or_units_or_model: Any,
) -> Tuple[DrawingUnit, float, float]:
    """
    Resolve target DrawingUnit, coordinate scale factor, and section scale factor
    from a struct_core Project, Metadata, Units, or StructuralModel.

    Returns
    -------
    unit : DrawingUnit
        The target drawing unit for modelspace entities (MM for metric, IN for imperial).
    coord_scale : float
        Multiplier to convert model coordinates into drawing units.
        (e.g., if model is in meters, 1000.0 to convert to mm; if in feet, 12.0 to convert to inches).
    sec_scale : float
        Multiplier to convert cross-section dimensions into drawing units.
    """
    units_obj = None

    # Project metadata units
    if hasattr(project_or_units_or_model, "metadata"):
        meta = getattr(project_or_units_or_model, "metadata", None)
        if meta and hasattr(meta, "units"):
            units_obj = meta.units

    # Direct units object
    if units_obj is None and hasattr(project_or_units_or_model, "length"):
        units_obj = project_or_units_or_model

    # Model units or is_metric attribute
    if units_obj is None and hasattr(project_or_units_or_model, "units"):
        units_obj = getattr(project_or_units_or_model, "units", None)

    if units_obj is not None:
        u_len = str(getattr(units_obj, "length", "")).strip().lower()
        if u_len in ("m", "meter", "meters", "metre", "metres"):
            return DrawingUnit.MM, 1000.0, 1000.0
        elif u_len in ("mm", "millimeter", "millimeters"):
            return DrawingUnit.MM, 1.0, 1.0
        elif u_len in ("cm", "centimeter", "centimeters"):
            return DrawingUnit.MM, 10.0, 10.0
        elif u_len in ("ft", "foot", "feet"):
            return DrawingUnit.IN, 12.0, 1.0
        elif u_len in ("in", "inch", "inches"):
            return DrawingUnit.IN, 1.0, 1.0

    # Check is_metric flag fallback
    is_m = getattr(project_or_units_or_model, "is_metric", None)
    if is_m is True:
        return DrawingUnit.MM, 1000.0, 1000.0
    elif is_m is False:
        return DrawingUnit.IN, 12.0, 1.0

    # Default to metric in mm
    return DrawingUnit.MM, 1000.0, 1000.0


def default_scale_for_view(
    view_type: str,
    is_metric: bool = True,
) -> DrawingScale:
    """Return the standard structural drafting scale for a given view type.

    Parameters
    ----------
    view_type : str
        Drawing view type ('plan', 'framing_plan', 'elevation', 'frame_elevation',
        'profile', 'beam_profile', 'section', 'detail', 'footing', 'staircase', 'slab').
    is_metric : bool, optional
        True for SI Metric (default), False for US Customary Imperial.

    Returns
    -------
    DrawingScale
        The standard default drawing scale for the view:
        - Plan: 1:100 (metric) or 1/8"=1'-0" (imperial)
        - Elevation: 1:50 (metric) or 1/4"=1'-0" (imperial)
        - Profile / Footing / Staircase: 1:25 (metric) or 1/2"=1'-0" (imperial)
        - Cross-Section / Detail: 1:30 or 1:20 (metric) or 1/2"=1'-0" (1:24 imperial)
    """
    vt = (view_type or "").lower().strip()
    if is_metric:
        if "plan" in vt and "slab" not in vt:
            return SCALE_1_100
        elif "elev" in vt:
            return SCALE_1_50
        elif "profile" in vt or "footing" in vt or "stair" in vt:
            return SCALE_1_25
        elif "slab" in vt and "plan" in vt:
            return SCALE_1_50
        elif "beam" in vt:
            return SCALE_1_30
        elif "sec" in vt or "detail" in vt:
            return SCALE_1_20
        return SCALE_1_50
    else:
        if "plan" in vt and "slab" not in vt:
            return SCALE_1_8_IN
        elif "elev" in vt:
            return SCALE_1_4_IN
        elif "profile" in vt or "footing" in vt:
            return SCALE_1_2_IN
        elif "stair" in vt:
            return SCALE_1_IN
        elif "beam" in vt:
            return SCALE_1_2_IN  # 1/2" = 1'-0" (1:24)
        elif "sec" in vt or "detail" in vt:
            return SCALE_1_IN
        return SCALE_1_4_IN


def format_length(val: float, is_metric: bool) -> str:
    """Format length/spacing value with explicit units (e.g. '216 mm' or '8.5"')."""
    if is_metric:
        return f"{int(round(val))} mm"
    else:
        if abs(val - round(val)) < 1e-3:
            return f'{int(round(val))}"'
        return f'{val:.1f}"'

