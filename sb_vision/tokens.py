"""Tokens detections, and the utilities to manipulate them."""

import math
import lzma
import pickle
import functools
from pathlib import Path

import numpy as np


def _row_mul(m, corner, col):
    return m[col, 0] * corner[0] + m[col, 1] * corner[1] + m[col, 2]


def _homography_transform(corner, homog):
    """
    Perform the equivalent of an OpenCV WarpPerspectiveTransform on the points.

    See http://bit.ly/2eQOTue for the equation.
    """
    z = _row_mul(homog, corner, 2)
    x = _row_mul(homog, corner, 0) / z
    y = _row_mul(homog, corner, 1) / z
    return x, y


def _decompose_homography(Homography, Calibration):
    """
    Python rewrite of the openCV function decomposeHomographyMat.

    :param Homography:
    :param Calibration:
    :return: Rotation list, Translation List, Normals List
    """
    # This would be the first step for properly calculating the relative
    # location of the marker
    pass


def _get_pixel_corners(homog):
    """
    Get the co-ordinate of the corners given the homography matrix.

    :param homog: Numpy array Homography matrix as returned from Apriltags
    :return: list of (x,y) pixel co-ordinates of the corners of the token
    """
    # Define the corners of the marker
    corners = np.array([(-1, -1), (-1, 1), (1, 1), (1, -1)])

    transformed = []

    for corner in corners:
        x, y = _homography_transform(corner, homog)
        transformed.append((x, y))

    return transformed


def _get_pixel_centre(homography_matrix):
    """Get the centre of the transform (ie how much translation there is)."""
    return _homography_transform((0, 0), homography_matrix)


@functools.lru_cache()
def _get_distance_model(name, image_size):
    if name is None:
        raise ValueError("Getting distance model of None")

    builtin_models_dir = Path(__file__).parent
    model_file = builtin_models_dir / '{}.pkl.xz'.format(name)

    with lzma.open(str(model_file), 'rb') as f:
        calibration = pickle.load(f)

    if calibration.resolution != image_size:
        raise ValueError(
            "Model {model} is calibrated for resolution {res_model}, not "
            "{res_this}".format(
                model=name,
                res_model=calibration.resolution,
                res_this=image_size,
            ),
        )

    return calibration


def _get_cartesian(
    homography_matrix,
    image_size,
    distance_model,
    marker_size,
):
    calibration = _get_distance_model(distance_model, image_size)
    flattened_homography_matrix = homography_matrix.ravel()

    (x,) = calibration.x_model.predict([flattened_homography_matrix])
    y = 0.0
    (z,) = calibration.z_model.predict([flattened_homography_matrix])

    position = np.array([x, y, z])

    # Adjust for marker size
    effective_marker_size = np.mean(marker_size)
    effective_marker_scale = effective_marker_size / 0.1

    return position * effective_marker_scale


DEFAULT_TOKEN_SIZE = (0.25, 0.25)


class Token:
    """Representation of the detection of one token."""

    def __init__(self, id, size=DEFAULT_TOKEN_SIZE, certainty=0.0):
        """
        General initialiser.

        This covers the main token properties but notably does _not_ populate
        the coordinate information.
        """
        self.id = id
        self.size = size
        self.certainty = certainty

    @classmethod
    def from_apriltag_detection(
        cls,
        apriltag_detection,
        sizes,
        image_size,
        distance_model
    ):
        """Construct a Token from an April Tag detection."""
        # *************************************************************************
        # NOTE: IF YOU CHANGE THIS PLEASE ADD THEM IN THE ROBOT-API camera.py
        # *************************************************************************

        instance = cls(
            id=apriltag_detection.id,
            size=sizes.get(apriltag_detection.id, DEFAULT_TOKEN_SIZE),
            certainty=apriltag_detection.goodness,
        )

        arr = [apriltag_detection.H.data[x] for x in range(9)]
        homography = np.reshape(arr, (3, 3))

        instance.infer_location_from_homography_matrix(
            homography_matrix=homography,
            distance_model=distance_model,
            image_size=image_size,
        )
        return instance

    def infer_location_from_homography_matrix(
        self,
        *,
        homography_matrix,
        distance_model,
        image_size
    ):
        """Infer coordinate information from a homography matrix."""
        # pixel coordinates of the corners of the marker
        self.pixel_corners = _get_pixel_corners(homography_matrix)
        # pixel coordinates of the centre of the marker
        self.pixel_centre = _get_pixel_centre(homography_matrix)
        self.homography_matrix = homography_matrix

        # We don't set cartesian coordinates in the absence of a
        # distance model.
        if distance_model is None:
            return

        # Cartesian Co-ordinates in the 3D World, relative to the camera
        # (as opposed to somehow being compass-aligned)
        self.cartesian = _get_cartesian(
            homography_matrix,
            image_size,
            distance_model,
            self.size,
        )

    def __repr__(self):
        """General debug representation."""
        return "Token: {}, certainty:{}".format(self.id, self.certainty)

    __str__ = __repr__

    def __eq__(self, other):
        """Equivalent relation partitioning by `id`."""
        if not isinstance(other, Token):
            return False

        return self.id == other.id
