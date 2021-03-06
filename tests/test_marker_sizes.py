"""Tests for marker sizing."""

from pathlib import Path
from typing import Dict, Tuple
from unittest import mock

from pytest import approx

from sb_vision import FileCamera, Vision
from sb_vision.camera_base import CameraBase

TEST_DATA = Path(__file__).parent / 'test_data'

# The expected error for the distances of markers should be within tolerances
EXPECTED_LARGE_DISTANCE = 2.5
EXPECTED_SMALL_DISTANCE = 1
EXPECTED_TOLERANCE = 0.15


def assertMarkerDistance(
    camera: CameraBase,
    *,
    marker_sizes: Dict[int, Tuple[float, float]],
    expected_distance: float
) -> None:
    """Assert that the processed distance is as expected for a marker size."""
    vision = Vision(camera)

    with mock.patch('sb_vision.tokens.MARKER_SIZES', marker_sizes):
        token, = vision.snapshot()

    dist = token.spherical.dist
    assert dist == approx(expected_distance, rel=EXPECTED_TOLERANCE)


def test_unknown_marker_size():
    """Test an unknown marker size defaults to the trained size."""
    # The c270 model is trained on 25cm markers; so it assume that all markers
    # are that size unless told otherwise.
    assertMarkerDistance(
        FileCamera(TEST_DATA / 'tecknet-10cm-at-1m.jpg', camera_model='C016'),
        marker_sizes={},
        expected_distance=EXPECTED_LARGE_DISTANCE,
    )


def test_large_marker_large_size():
    """Test a marker matching the trained size has the right distance."""
    assertMarkerDistance(
        FileCamera(TEST_DATA / 'tecknet-25cm-at-2.5m.jpg', camera_model='C016'),
        marker_sizes={23: (0.25, 0.25)},
        expected_distance=EXPECTED_LARGE_DISTANCE,
    )


def test_large_marker_small_size():
    """
    Test image with large marker gives small distance when configured for a small marker.
    """
    assertMarkerDistance(
        FileCamera(TEST_DATA / 'tecknet-25cm-at-2.5m.jpg', camera_model='C016'),
        marker_sizes={23: (0.1, 0.1)},
        expected_distance=EXPECTED_SMALL_DISTANCE,
    )


def test_small_marker_large_size():
    """
    Test image with small marker gives large distance when configured for a large marker.
    """
    assertMarkerDistance(
        FileCamera(TEST_DATA / 'tecknet-10cm-at-1m.jpg', camera_model='C016'),
        marker_sizes={44: (0.25, 0.25)},
        expected_distance=EXPECTED_LARGE_DISTANCE,
    )


def test_small_marker_small_size():
    """
    Test image with small marker gives small distance when configured for a small marker.
    """
    assertMarkerDistance(
        FileCamera(TEST_DATA / 'tecknet-10cm-at-1m.jpg', camera_model='C016'),
        marker_sizes={44: (0.1, 0.1)},
        expected_distance=EXPECTED_SMALL_DISTANCE,
    )
