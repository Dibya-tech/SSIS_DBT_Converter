"""Convert SVG diagram strings to PNG bytes for zip export."""
from __future__ import annotations

import io
import re


def svg_to_png_bytes(svg_str: str, dpi: int = 144) -> bytes | None:
    """Return PNG bytes from an SVG string, or None if svglib is unavailable."""
    try:
        from svglib.svglib import svg2rlg          # type: ignore
        from reportlab.graphics import renderPM    # type: ignore
    except ImportError:
        return None

    try:
        # svglib needs a proper XML declaration; add one if missing
        if not svg_str.lstrip().startswith("<?xml"):
            svg_str = '<?xml version="1.0" encoding="utf-8"?>\n' + svg_str

        buf_in = io.BytesIO(svg_str.encode("utf-8"))
        drawing = svg2rlg(buf_in)
        if drawing is None:
            return None

        buf_out = io.BytesIO()
        renderPM.drawToFile(drawing, buf_out, fmt="PNG", dpi=dpi)
        return buf_out.getvalue()
    except Exception:
        return None
