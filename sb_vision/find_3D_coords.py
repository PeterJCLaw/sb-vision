"""
Handlers for detecting 3D marker Location.

Also handles loading the calibration file which is passed into the
location finding function.
"""

import functools
import re
import xml.etree.ElementTree as etree
from pathlib import Path
from typing import List, Tuple, cast

import cv2
import numpy as np

from sb_vision.coordinates import Cartesian, PixelCoordinate


def _get_values_from_xml_element(element: etree.Element) -> List[str]:
    """Parse an xml tag with space-separated variables."""
    text = []  # type: List[str]
    for e in element.itertext():
        e = e.strip()
        if e:
            text += re.split(r'\s+', e)
    return text


def _find_element(root: etree.Element, descendant_name: str) -> etree.Element:
    """
    Finds a descendant element by name or raises an error if no descendant exists.
    """
    descendant = root.find(descendant_name)
    if descendant is None:
        raise Exception("{} has no descendant {!r}".format(root.tag, descendant_name))
    return descendant


def _parse_matrix_xml_element(element: etree.Element) -> List[List[np.float64]]:
    """Converts an element containing an OpenCV matrix to python lists."""
    type_id = element.attrib.get('type_id')
    if type_id != 'opencv-matrix':
        raise ValueError('Unexpected type_id of tag ({})'.format(type_id))
    data_type = _find_element(element, 'dt').text
    if data_type != 'd':  # doubles
        raise ValueError('Invalid data type in element {}'.format(
            element.tag,
        ))
    # Element.text can apparently be 'bytes' and 'SupportsInt' as well as 'str'.
    # In our usage we only ever see 'str', so these ignores are safe.
    rows = int(_find_element(element, 'rows').text)  # type: ignore
    cols = int(_find_element(element, 'cols').text)  # type: ignore

    values = _get_values_from_xml_element(_find_element(element, 'data'))
    data = cast(List[List[np.float64]], np.reshape(
        [float(v) for v in values],
        (rows, cols),
    ).tolist())
    return data


def get_calibration(file_name: Path) -> Tuple[List[List[float]], List[List[float]]]:
    """
    Parse a calibration xml generated by the camera calibration tool.

    (see https://docs.opencv.org/3.4.0/d7/d21/tutorial_interactive_calibration.html)
    :param file_name: name of xml file to parse
    :return: calibrations from the file in a dictionary
    """
    with file_name.open() as file:
        tree = etree.parse(file)
        root = tree.getroot()
        camera_matrix = _parse_matrix_xml_element(
            _find_element(root, 'cameraMatrix'),
        )
        dist_coeffs = _parse_matrix_xml_element(
            _find_element(root, 'dist_coeffs'),
        )

    return camera_matrix, dist_coeffs


@functools.lru_cache()
def load_camera_calibrations(camera_model: str) -> Tuple[List[List[float]],
                                                         List[List[float]]]:
    """
    Load camera calibrations from a file.

    :param camera_model: file to load
    :return: camera calibrations
    """
    builtin_models_dir = Path(__file__).parent
    model_file = builtin_models_dir / '{}_calibration.xml'.format(
        camera_model,
    )

    camera_matrix, distance_coefficients = get_calibration(model_file)
    return camera_matrix, distance_coefficients


def calculate_transforms(
    marker_size: Tuple[float, float],
    pixel_corners: List[PixelCoordinate],
    camera_matrix: List[List[float]],
    distance_coefficients: List[List[float]],
) -> Tuple[Cartesian, Tuple[float, float, float]]:
    """
    Calculate the position of a marker.

    Given the pixel co-ordinates of the corners and the calibrations
    of the camera.

    :param marker_size: size of the marker
    :param pixel_corners: pixel co-ordinates of the corners of the marker
        (clockwise around the marker from the top-left corner)
    :param camera_matrix: calibration matrix for the camera
    :param distance_coefficients: distance calibration for the camera
    :return: translation and orientation of the marker
    """
    w, h = marker_size
    width_from_centre = w / 2
    height_from_centre = h / 2

    # create the rectangle representing the marker in 3D
    object_points = np.array([
        [width_from_centre, height_from_centre, 0],
        [width_from_centre, -height_from_centre, 0],
        [-width_from_centre, -height_from_centre, 0],
        [-width_from_centre, height_from_centre, 0],
    ])

    return_value, orientation_vector, translation_vector = cv2.solvePnP(
        object_points,
        np.array(pixel_corners),
        np.array(camera_matrix),
        np.array(distance_coefficients),
    )
    if not return_value:
        raise ValueError("cv2.solvePnP returned false")

    translation_vector = Cartesian(*(v[0] for v in translation_vector))
    # OpenCV returns co-ordinates where a positive Y is downwards
    translation_vector = Cartesian(
        translation_vector.x,
        -translation_vector.y,
        translation_vector.z,
    )

    orientation_vector = cast(
        Tuple[float, float, float],
        tuple(v[0] for v in orientation_vector),
    )

    return translation_vector, orientation_vector
