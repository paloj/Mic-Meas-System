import numpy as np
from scipy.ndimage import uniform_filter1d


def smooth_response(magnitude_db, window_bins=5):
    """
    Apply simple moving average smoothing to dB response.
    """
    return uniform_filter1d(magnitude_db, size=window_bins)


def normalize_response(response_db, reference_db):
    """
    Subtract reference response from mic response to normalize.
    """
    return response_db - reference_db


def db_to_linear(db):
    """
    Convert decibel value to linear scale.
    """
    return 10 ** (db / 20)


def linear_to_db(linear):
    """
    Convert linear magnitude to decibels.
    """
    linear = np.maximum(linear, 1e-12)
    return 20 * np.log10(linear)
