"""Tests for struct_draw.elements.beam_profile."""

from __future__ import annotations

import unittest
from struct_draw.core.data import BeamProfileData
from struct_draw.elements.beam_profile import profile_view, section_views, drawing


class MockTarget:
    """Mock CAD modelspace target to collect drawn entities."""

    def __init__(self):
        self.entities = []

    def add_line(self, start, end, dxfattribs=None):
        self.entities.append(("line", start, end, dxfattribs))
        return self

    def add_polyline2d(self, points, dxfattribs=None, close=False):
        self.entities.append(("polyline", points, dxfattribs))
        return self

    def add_lwpolyline(self, points, dxfattribs=None, close=False):
        self.entities.append(("polyline", points, dxfattribs))
        return self

    def add_circle(self, center, radius, dxfattribs=None):
        self.entities.append(("circle", center, radius, dxfattribs))
        return self

    def add_text(self, text, dxfattribs=None):
        self.entities.append(("text", text, dxfattribs))
        return self

    def add_mtext(self, text, dxfattribs=None):
        class MockDXF:
            def __init__(self):
                self.width = 0.0
                self.char_height = 0.0
        class MockMText:
            def __init__(self):
                self.dxf = MockDXF()
            def set_location(self, pos, attachment_point=None):
                pass
        self.entities.append(("mtext", text, dxfattribs))
        return MockMText()

    def add_linear_dim(self, base, p1, p2, dxfattribs=None, override=None, **kwargs):
        class MockDim:
            def render(self):
                pass
            def set_text(self, text):
                pass
        self.entities.append(("dim", p1, p2, override, dxfattribs))
        return MockDim()

    def add_aligned_dim(self, p1, p2, distance=1.0, text="", dxfattribs=None):
        self.entities.append(("dim", p1, p2, text, dxfattribs))
        return self


class TestBeamProfile(unittest.TestCase):

    def test_beam_profile_from_metric(self):
        data = BeamProfileData.from_metric(
            name="PB-1",
            grid_line_name="A-A",
            spans_mm=[5500.0, 4000.0, 3000.0, 4000.0, 5500.0],
            col_width_mm=450.0,
            beam_depth_mm=450.0,
            cover_mm=40.0,
        )
        self.assertTrue(data.is_metric)
        self.assertEqual(len(data.spans_in), 5)
        self.assertEqual(data.col_width_in, 450.0)

    def test_profile_view_drawing(self):
        data = BeamProfileData.from_metric()
        target = MockTarget()
        refs = profile_view(target, data)
        self.assertIn("origin", refs)
        self.assertIn("spans", refs)
        self.assertGreater(len(target.entities), 20)

    def test_section_views_drawing(self):
        data = BeamProfileData.from_metric()
        target = MockTarget()
        refs = section_views(target, data)
        self.assertIn("origin_sec1", refs)
        self.assertIn("origin_sec2", refs)
        self.assertGreater(len(target.entities), 10)

    def test_drawing_master_function(self):
        data = BeamProfileData.from_metric()
        target = MockTarget()
        refs = drawing(target, data)
        self.assertIn("profile", refs)
        self.assertIn("sections", refs)
        self.assertGreater(len(target.entities), 30)


if __name__ == "__main__":
    unittest.main()
