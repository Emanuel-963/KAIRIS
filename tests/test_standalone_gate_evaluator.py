import math

import numpy as np

from scripts.evaluate_standalone_gates import numeric_equivalent


def test_numeric_equivalent_preserves_nan_positions_and_tolerances():
    passed, error = numeric_equivalent(
        [1.0, None, 3.0], np.array([1.0 + 1e-12, np.nan, 3.0]), 1e-10, 1e-12
    )

    assert passed
    assert error < 1e-10


def test_numeric_equivalent_rejects_shape_or_nan_mismatch():
    shape_passed, shape_error = numeric_equivalent([1.0], [1.0, 2.0], 1e-10, 1e-12)
    nan_passed, nan_error = numeric_equivalent([1.0, None], [1.0, 2.0], 1e-10, 1e-12)

    assert not shape_passed and math.isinf(shape_error)
    assert not nan_passed and math.isinf(nan_error)
