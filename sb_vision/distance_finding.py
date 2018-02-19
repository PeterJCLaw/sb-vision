"""
Handlers for detecting 3D marker Location.

Also handles loading the calibration file which is passed into the
location finding function.
"""

import functools
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from lxml import etree

from sb_vision.coordinates import PixelCoordinate


def _get_values_from_xml_element(element: etree.Element) -> List[str]:
    """Parse an xml tag with space-separated variables."""
    text = []  # type: List[str]
    for e in element.itertext():
        e = e.strip()
        if e:
            text += re.split(r'\s+', e.replace('\n', ''))
    return text


def get_calibration(file_name: Path) -> Dict[str, Any]:
    """
    Parse a calibration xml generated by the camera calibration tool.

    (see https://docs.opencv.org/3.4.0/d7/d21/tutorial_interactive_calibration.html)
    :param file_name: name of xml file to parse
    :return: calibrations from the file in a dictionary
    """
    calibrations = {}
    with file_name.open() as file:
        tree = etree.parse(file)
        root = tree.getroot()
        for element in root:
            if element.tag in ['dist_coeffs', 'cameraMatrix']:
                if element.attrib.get('type_id') == 'opencv-matrix':
                    data_type = element.find('dt').text
                    if data_type != 'd':  # doubles
                        raise ValueError('Invalid data type in xml file {}'.format(
                            file_name,
                        ))
                    rows = int(element.find('rows').text)
                    cols = int(element.find('cols').text)

                    values = _get_values_from_xml_element(element.find('data'))
                    data = np.reshape(
                        [float(v) for v in values],
                        (rows, cols),
                    ).tolist()
                    calibrations[element.tag] = data

                else:
                    raise ValueError('Unexpected type of tag in xml file {}'.format(
                        file_name,
                    ))
    return calibrations


@functools.lru_cache()
def load_camera_calibrations(camera_model: str) -> Tuple[List[List[float]],
                                                         List[List[float]]]:
    """
    Load camera calibrations from a file.

    :param file_name: file to load
    :return: camera calibrations
    """
    builtin_models_dir = Path(__file__).parent
    model_file = builtin_models_dir / '{}_calibration.xml'.format(
        camera_model,
    )
    calibrations = get_calibration(model_file)
    camera_matrix = calibrations['cameraMatrix']
    distance_coefficents = calibrations['dist_coeffs']
    return camera_matrix, distance_coefficents


def calculate_transforms(
    marker_size: Tuple[float, float],
    pixel_corners: List[PixelCoordinate],
    camera_matrix: List[List[float]],
    distance_coefficients: List[List[float]],
):
    """
    Calculate the position of a marker.

    given the pixel co-ordinates of the corners and the calibrations
    of the camera.

    :param marker_size: size of the marker
    :param pixel_coords: pixel co-ordinates of the corners of the marker
        (clockwise around the marker)
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

    _, orientation_vector, translation_vector = cv2.solvePnP(
        object_points,
        np.array(pixel_corners),
        np.array([np.array(xi) for xi in camera_matrix]),
        np.array([np.array(xi) for xi in distance_coefficients]),
    )
    translation_vector = tuple(v[0] for v in translation_vector)
    orientation_vector = tuple(v[0] for v in orientation_vector)

    return translation_vector, orientation_vector
