import functools
from typing import Tuple, Dict

import cv2
from lxml import etree
import re
import numpy as np


def _get_text(element: etree.Element):
    """parse an xml tag with space-separated variables"""
    text = []
    for e in element.itertext():
        if e.strip():
            text += re.split('\s+', re.sub('\n', '', e.strip()))
    return text


def get_calibration(file_name: str) -> Dict:
    """
    Parse a calibration xml generated by the camera calibration tool
    (see https://docs.opencv.org/3.4.0/d7/d21/tutorial_interactive_calibration.html)
    :param file_name: name of xml file to parse
    :return: calibrations from the file in a dictionary
    """
    calibrations = {}
    with open(file_name) as file:
        tree = etree.parse(file)
        root = tree.getroot()
        for element in root:
            if 'type_id' in element.attrib and element.attrib[
                 'type_id'] == 'opencv-matrix':
                rows, cols = int(element.find('rows').text), int(
                    element.find('cols').text)
                data_type = element.find('dt').text
                values = _get_text(element.find('data'))
                if data_type == 'd':  # doubles
                    data = np.reshape(np.array([float(v) for v in values]),
                                      (rows, cols))
                else:
                    raise ValueError('Invalid data type in xml')
            # Integer tag names
            elif element.tag in ['framesCount', 'cameraResolution']:
                values = _get_text(element)
                data = [int(v) for v in values]
            elif element.tag in ['avg_reprojection_error']:
                values = _get_text(element)
                data = [float(v) for v in values]
            else:
                data = _get_text(element)
            calibrations[element.tag] = data
    return calibrations


@functools.lru_cache()
def load_camera_calibrations(file_name: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load camera calibrations from a file
    :param file_name: file to load
    :return: camera calibrations
    """
    calibrations = get_calibration(file_name)
    camera_matrix = calibrations['cameraMatrix']
    distance_coefficents = calibrations['dist_coeffs']
    return camera_matrix, distance_coefficents


def calculate_transforms(
        marker_size: Tuple[float, float],
        pixel_coords: np.ndarray,
        camera_matrix: np.ndarray,
        distance_coefficients: np.ndarray):
    """
    Calculate the position of a marker given the pixel co-ordinates of the
    corners and the calibrations of the camera.
    :param marker_size: size of the marker
    :param pixel_coords: pixel co-ordinates of the corners of the marker
        (clockwise around the marker)
    :param camera_matrix: calibration matrix for the camera
    :param distance_coefficients: distance calibration for the camera
    :return: translation and orientation of the marker
    """
    x, y = marker_size
    x /= 2
    y /= 2

    # create the rectangle representing the marker in 3D
    object_points = np.array([
        [x, y, 0],
        [x, -y, 0],
        [-x, -y, 0],
        [-x, y, 0]
    ])

    retval, orientation_vector, translation_vector = cv2.solvePnP(
        object_points,
        pixel_coords,
        camera_matrix,
        distance_coefficients,
    )
    translation_vector = tuple(x[0] for x in translation_vector)
    orientation_vector = tuple(x[0] for x in orientation_vector)

    return translation_vector, orientation_vector
