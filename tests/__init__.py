"""Tests for the struct_draw package.

Run with::

    pytest

or::

    pytest tests/

The tests are deliberately self-contained: they build their own
DrawingInputs from scratch and never import ``aci318`` /
``struct_core``, so the test suite runs in isolation.
"""