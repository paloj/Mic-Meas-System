import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve
from scipy.fft import rfft, rfftfreq
import os


def deconvolve(recorded, sweep, epsilon=1e-8):
    """
    Deconvolve recorded signal with known sweep.
    Returns impulse response.
    """
    # Time-reverse sweep
    inv_sweep = sweep[::-1] / (np.max(np.abs(sweep)) + epsilon)
    ir = fftconvolve(recorded, inv_sweep, mode='full')
    return ir


def compute_frequency_response(ir, fs):
    """
    Compute magnitude spectrum from impulse response.
    Returns frequency bins and dB magnitude.
    """
    N = len(ir)
    windowed = ir[:fs] * np.hanning(fs)  # Window 1 second
    spectrum = np.abs(rfft(windowed))
    spectrum[spectrum == 0] = 1e-12
    magnitude_db = 20 * np.log10(spectrum)
    freqs = rfftfreq(len(windowed), 1 / fs)
    return freqs, magnitude_db


def process_mic_recordings(folder, sweep_path="test_signals/sweep.wav", fs=48000, reference_db=None, smoothing_bins=5):
    """
    Load 3 takes, compute average and smoothed frequency response, optionally normalize.
    """
    from utils import smooth_response, normalize_response

    sweep, _ = sf.read(sweep_path)
    responses = []
    for i in range(1, 4):
        rec_path = os.path.join(folder, f"mic_take_{i}.wav")
        recorded, _ = sf.read(rec_path)
        signal = recorded[:, 0] if recorded.ndim > 1 else recorded
        ir = deconvolve(signal, sweep)
        freqs, mag_db = compute_frequency_response(ir, fs)
        responses.append(mag_db)

    avg_response = np.mean(responses, axis=0)
    std_response = np.std(responses, axis=0)

    smoothed = smooth_response(avg_response, window_bins=smoothing_bins)

    if reference_db is not None:
        normalized = normalize_response(smoothed, reference_db)
    else:
        normalized = None

    print("[✓] Processed frequency response from 3 takes.")
    return freqs, smoothed, std_response, normalized


if __name__ == "__main__":
    freqs, avg_db, std_db = process_mic_recordings("test_mic_recordings")
    print(f"Frequencies: {freqs.shape}, Response: {avg_db.shape}")