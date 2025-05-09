
#processor.py
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
    N = min(len(ir), fs)
    windowed = ir[:N] * np.hanning(N)  # Window 1 second
    spectrum = np.abs(rfft(windowed))
    spectrum[spectrum == 0] = 1e-12
    magnitude_db = 20 * np.log10(spectrum)
    freqs = rfftfreq(len(windowed), 1 / fs)
    return freqs, magnitude_db


def process_mic_recordings(folder, sweep_path="test_signals/sweep.wav", fs=48000, reference_db=None, smoothing_bins=5, anomaly_threshold_db=6):
    """
    Load 3 takes, compute average and smoothed frequency response, optionally normalize.
    """
    from utils import smooth_response, normalize_response

    sweep, _ = sf.read(sweep_path)
    responses = []
    anomalies = []
    import glob

    mic_files = sorted(glob.glob(os.path.join(folder, "mic_take_*.wav")))
    for i, rec_path in enumerate(mic_files, 1):
        recorded, _ = sf.read(rec_path)
        signal = recorded[:, 0] if recorded.ndim > 1 else recorded
        ir = deconvolve(signal, sweep)
        freqs, mag_db = compute_frequency_response(ir, fs)
        responses.append(mag_db)

    responses = np.array(responses)
    avg_response = np.mean(responses, axis=0)
    # Anomaly detection: any response deviating more than threshold from mean
    for i, r in enumerate(responses):
        if np.any(np.abs(r - avg_response) > anomaly_threshold_db):
            anomalies.append(i + 1)
    std_response = np.std(responses, axis=0)

    smoothed = smooth_response(avg_response, window_bins=smoothing_bins)

    if reference_db is not None:
        normalized = normalize_response(smoothed, reference_db)
    else:
        normalized = None

    print("[✓] Processed frequency response from 3 takes.")
    if anomalies:
        print(f"[!] Anomaly detected in take(s): {anomalies}")
    return freqs, smoothed, std_response, normalized


if __name__ == "__main__":
    freqs, avg_db, std_db, _ = process_mic_recordings("test_mic_recordings")
    print(f"Frequencies: {freqs.shape}, Response: {avg_db.shape}")
