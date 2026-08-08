"""struct_draw.core.document — Thin ezdxf wrappers.

This module is the **only** place that imports ``ezdxf`` for the
purpose of *managing* an ``ezdxf.Drawing``. The element library
and primitives operate on whatever target is passed to them; this
module is responsible for:

* creating a fresh ``ezdxf.Drawing`` with the standard ``R2018``
  setup,
* registering style tables (line types, text styles, layers,
  blocks, dimension styles) from the :mod:`struct_draw.style`
  registries,
* setting up layouts (paper space tabs) with paper size and
  margins.

By keeping these responsibilities here, the rest of the package
remains free of ezdxf-specific imports (until the very last step
where the backend calls :func:`save`).
"""

from __future__ import annotations

from typing import Any, Iterable

from struct_draw.utils.exceptions import BackendError


def new_drawing(dxfversion: str = "R2018", setup: bool = True) -> Any:
    """Create a new ``ezdxf.Drawing`` populated with default tables.

    Parameters
    ----------
    dxfversion
        DXF format version. Defaults to ``"R2018"`` which is the
        modern, broadly-supported baseline.
    setup
        Whether to populate default line types / text styles /
        layers (ezdxf ``setup=True``).
    """
    try:
        import ezdxf  # lazy import — keeps `import struct_draw` cheap
    except ImportError as exc:  # pragma: no cover
        raise BackendError(
            "DXF output requires the 'ezdxf' package. "
            "Install it with: pip install 'struct_draw[dxf]' "
            "(or: pip install ezdxf)."
        ) from exc

    return ezdxf.new(dxfversion=dxfversion, setup=setup)


# ---------------------------------------------------------------------------
# Style-table registration
# ---------------------------------------------------------------------------


def ensure_linetype(doc: Any, name: str, pattern: Iterable[float] | None = None, *, description: str = "") -> Any:
    """Create a line type on ``doc`` if not already present."""
    if name in doc.linetypes:
        return doc.linetypes.get(name)
    if not pattern:
        return doc.linetypes.add(name=name, pattern=[0.0], description=description)
    return doc.linetypes.add(name=name, pattern=list(pattern), description=description)


def ensure_text_style(
    doc: Any,
    name: str,
    *,
    font: str = "txt",
    height: float = 0.0,
    width_factor: float = 1.0,
    oblique_angle: float = 0.0,
) -> Any:
    """Create or update a text style on ``doc``."""
    if name in doc.styles:
        style = doc.styles.get(name)
    else:
        style = doc.styles.add(name=name, font=font)
    if height:
        style.dxf.last_height = height
    if width_factor:
        style.dxf.width = width_factor
    if oblique_angle:
        style.dxf.oblique = oblique_angle
    return style


def ensure_layer(
    doc: Any,
    *,
    name: str,
    color: int | None = None,
    linetype: str = "Continuous",
    lineweight: int = -1,
    on: bool = True,
    plot: bool = True,
    description: str = "",
) -> Any:
    """Create or update a layer on ``doc``."""
    if name in doc.layers:
        layer = doc.layers.get(name)
        if color is not None:
            layer.color = color
    else:
        kwargs: dict[str, Any] = {"name": name}
        if color is not None:
            kwargs["color"] = color
        doc.layers.add(**kwargs)
        layer = doc.layers.get(name)
    layer.linetype = linetype
    if lineweight >= 0:
        layer.dxf.lineweight = lineweight
    layer.on = on
    layer.plot = plot
    if description:
        layer.description = description
    return layer


def ensure_block(doc: Any, *, name: str, base_point: tuple[float, float] = (0.0, 0.0)) -> Any:
    """Create (or return) a block definition with the given name."""
    if name in doc.blocks:
        return doc.blocks.get(name)
    return doc.blocks.new(name=name, base_point=base_point)


def ensure_dim_style(
    doc: Any,
    *,
    name: str,
    textstyle: str = "Standard",
    arrow_size: float = 0.10,
    extension_offset: float = 0.0625,
    extension_extension: float = 0.125,
) -> Any:
    """Create or update a dimension style on ``doc``.

    We deliberately call :py:meth:`DimStyleTable.add` with **only**
    ``name=`` and then poke the remaining properties via DXF group
    codes. Different ``ezdxf`` versions expose slightly different
    keyword names for the same properties (``textstyle`` vs
    ``text_style``, ``dimblk`` family renames, etc.) — group codes
    are the stable contract and work across all versions.
    """
    if name in doc.dimstyles:
        style = doc.dimstyles.get(name)
    else:
        style = doc.dimstyles.add(name=name)

    # Map of group-code -> value. We set whatever we can; missing
    # group codes (older ezdxf releases) are tolerated via try/except.
    pairs: list[tuple[str, Any]] = [
        ("dimtxsty", textstyle),       # 340 — dimension text style
        ("dimasz", arrow_size),        #  41 — arrow size
        ("dimexo", extension_offset),  #  42 — extension line offset
        ("dimexe", extension_extension),  #  44 — extension line extension
    ]
    for code, value in pairs:
        try:
            style.dxf.setattr(code, value)
        except Exception:
            pass
    return style


def ensure_layout(
    doc: Any,
    *,
    name: str,
    paper_size: tuple[float, float],
    margins: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    units: str = "inch",
) -> Any:
    """Create or return a layout tab with the given paper setup."""
    layout = doc.layouts.get(name) or doc.layouts.new(name)
    layout.page_setup(size=paper_size, margins=margins, units=units)
    return layout


def register_all_styles(
    doc: Any,
    *,
    layers: Any | None = None,
    linetypes: Any | None = None,
    text_styles: Any | None = None,
    dimension_styles: Any | None = None,
    blocks: Any | None = None,
) -> None:
    """Register every style registry on ``doc``.

    Any argument may be ``None`` — that registry is skipped. The
    caller is responsible for passing fully-populated registries;
    this function never invents defaults.
    """
    if linetypes is not None:
        for lt in linetypes.linetypes.values():
            ensure_linetype(doc, name=lt.name, pattern=lt.pattern, description=lt.description)
    if text_styles is not None:
        for ts in text_styles.text_styles.values():
            ensure_text_style(
                doc,
                name=ts.name,
                font=ts.font,
                height=ts.height,
                width_factor=ts.width_factor,
                oblique_angle=ts.oblique_angle,
            )
    if layers is not None:
        for layer in layers.layers.values():
            ensure_layer(
                doc,
                name=layer.name,
                color=layer.color,
                linetype=layer.linetype,
                lineweight=layer.lineweight,
                on=layer.on,
                plot=layer.plot,
                description=layer.description,
            )
    if dimension_styles is not None:
        for ds in dimension_styles.styles.values():
            ensure_dim_style(
                doc,
                name=ds.name,
                textstyle=ds.text_style,
                arrow_size=ds.arrow_size,
                extension_offset=ds.extension_offset,
                extension_extension=ds.extension_extension,
            )
    if blocks is not None:
        for block in blocks.blocks.values():
            blk = ensure_block(doc, name=block.name, base_point=block.base_point)
            for prim in block.primitives:
                _emit_block_primitive(blk, prim)


def _emit_block_primitive(block: Any, prim: dict[str, Any]) -> None:
    """Append one primitive entry to a block definition."""
    kind = prim.get("kind")
    if kind == "line":
        block.add_line(prim["start"], prim["end"])
    elif kind == "circle":
        block.add_circle(prim["center"], prim["radius"])
    elif kind == "arc":
        block.add_arc(
            prim["center"],
            prim["radius"],
            prim["start_angle"],
            prim["end_angle"],
        )
    elif kind == "polyline":
        block.add_lwpolyline(prim["points"], close=prim.get("close", True))
    elif kind == "text":
        block.add_text(
            prim["text"],
            height=prim.get("height", 0.10),
            dxfattribs={"insert": prim["position"]},
        )
    else:
        raise BackendError(f"Unknown block primitive kind: {kind!r}")


__all__ = [
    "new_drawing",
    "ensure_linetype",
    "ensure_text_style",
    "ensure_layer",
    "ensure_block",
    "ensure_dim_style",
    "ensure_layout",
    "register_all_styles",
]