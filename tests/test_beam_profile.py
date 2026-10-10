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
            spans=[5500.0, 4000.0, 3000.0, 4000.0, 5500.0],
            col_width=450.0,
            beam_depth=450.0,
            cover=40.0,
        )
        self.assertTrue(data.is_metric)
        self.assertEqual(len(data.spans_in), 5)
        self.assertEqual(data.col_width_in, 450.0)

    def test_beam_profile_from_metric_invalid_alias_raises(self):
        with self.assertRaises(TypeError):
            BeamProfileData.from_metric(
                name="PB-1",
                spans_mm=[5500.0, 4000.0],  # type: ignore
            )

    def test_beam_profile_from_imperial(self):
        data = BeamProfileData.from_imperial(
            name="PB-1",
            grid_line_name="A-A",
            spans=[216.0, 160.0, 120.0, 160.0, 216.0],
            col_width=18.0,
            beam_depth=18.0,
            cover=1.5,
        )
        self.assertFalse(data.is_metric)
        self.assertEqual(len(data.spans_in), 5)
        self.assertEqual(data.col_width_in, 18.0)

    def test_footing_from_imperial(self):
        from struct_draw.core.data import FootingData, IsolatedFootingData
        footing = FootingData.from_imperial(
            name="F1",
            length=72.0,
            width=72.0,
            mid_thick=18.0,
            edge_thick=10.0,
            col_width=16.0,
            col_depth=16.0,
            col_height=96.0,
            fd_depth=60.0,
            pl_height=24.0,
            cover=3.0,
            bar_dia=0.625,
            bar_spacing=6.0,
            ld=24.0,
        )
        self.assertIsInstance(footing, IsolatedFootingData)
        self.assertFalse(footing.is_metric)
        self.assertEqual(footing.length_in, 72.0)
        self.assertEqual(footing.mid_thickness_in, 18.0)

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
