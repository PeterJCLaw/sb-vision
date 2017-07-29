"""Utility to derive calibration matrix from training examples."""

import numpy
import numpy.linalg
import scipy.linalg
import scipy.optimize
import collections

Calibration = collections.namedtuple('Calibration', (
    'focal_length',
))


def fit(training_examples):
    """Fit calibration matrix to given iterable of training examples."""

    training_examples = list(training_examples)

    def reconstruction_error(x, print_things=False):
        [focal_length] = x

        total_error = 0.0

        for x in training_examples:
            calibration_matrix = numpy.array([
                [x.size[0] * focal_length, 0.0, 0.5 * x.size[0]],
                [0.0, x.size[1] * focal_length, 0.5 * x.size[1]],
                [0.0, 0.0, 1.0],
            ])

            error_levels = []

            for rotation in (
                (1, 0, 0, 1),
                (0, -1, 1, 0),
                (-1, 0, 0, -1),
                (0, 1, -1, 0),
            ):
                a, b, c, d = rotation

                pose_matrix = numpy.array([
                    [a, b, 0.0, x.x_offset_right],
                    [c, d, 0.0, 0.0],
                    [0.0, 0.0, 1.0, x.z_distance],
                ])

                homography_matrix_with_extra_col = numpy.array([
                    x.homography_matrix[:, 0],
                    x.homography_matrix[:, 1],
                    numpy.cross(
                        x.homography_matrix[:, 0],
                        x.homography_matrix[:, 1],
                    ),
                    x.homography_matrix[:, 2],
                ]).T

                solved_pose_matrix, _, _, _ = scipy.linalg.lstsq(
                    calibration_matrix,
                    homography_matrix_with_extra_col,
                )

                if print_things:
                    print(pose_matrix)
                    print(solved_pose_matrix)

                error_levels.append(
                    numpy.linalg.norm(
                        (pose_matrix - solved_pose_matrix)[:, 3]
                    ),
                )

            total_error += max(error_levels)

        return total_error / len(training_examples)

    initial_focal_length = 1.0  # 1m

    result = scipy.optimize.minimize(
        reconstruction_error,
        x0=[
            initial_focal_length,
        ],
        method='Nelder-Mead',
    )
    print(result)

    fre = reconstruction_error(result.x, print_things=True)
    print("Mean error: ", fre)

    final_focal_length, = \
        result.x

    return Calibration(
        focal_length=final_focal_length / 0.1,
    )
