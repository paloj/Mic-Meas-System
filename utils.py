#utils.py
import numpy as np
from scipy.ndimage import uniform_filter1d


def smooth_response(magnitude_db, window_bins=5):
    """
    Apply simple moving average smoothing to dB response.
    """
    return uniform_filter1d(magnitude_db, size=window_bins)

def smooth_octave(freqs, magnitude_db, fraction=3):
    """
    Apply fractional octave smoothing in log-frequency domain.
    fraction: 1 for 1-octave, 3 for 1/3 octave, etc.
    """
    smoothed = np.zeros_like(magnitude_db)
    for i, f in enumerate(freqs):
        if f <= 0:
            smoothed[i] = magnitude_db[i]
            continue
        f_low = f / 2 ** (1 / (2 * fraction))
        f_high = f * 2 ** (1 / (2 * fraction))
        mask = (freqs >= f_low) & (freqs <= f_high)
        if np.any(mask):
            smoothed[i] = np.mean(magnitude_db[mask])
        else:
            smoothed[i] = magnitude_db[i]
    return smoothed

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
