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

def detect_anomalies(name, path, anomaly_threshold_db, pattern="mic_take_*.wav", sweep_path="test_signals/sweep.wav"):
    from processor import process_mic_recordings as check_anomalies, compute_frequency_response, deconvolve
    from plotter import plot_frequency_response
    from utils import smooth_response
    import matplotlib.pyplot as plt
    import soundfile as sf
    import glob
    import os
    import shutil
    import time

    print(f"[⚠] Checking for anomalies in {name} recordings...")
    # Check for anomalies in the recordings
    freqs, smoothed, std, _, anomalies = check_anomalies(path, return_anomalies=True, anomaly_threshold_db=anomaly_threshold_db)
    if anomalies:
        print(f"[⚠] Anomalies detected in takes: {anomalies}\n")
        # Plot the frequency response with anomalies highlighted
        anomaly_plot = os.path.join("output", f"{name}_anomaly_debug.png")
        takes = sorted(glob.glob(os.path.join(path, pattern)))
        sweep, _ = sf.read(sweep_path)
        plt.figure(figsize=(10, 6))
        for take in takes:
            signal, _ = sf.read(take)
            ir = deconvolve(signal[:, 0] if signal.ndim > 1 else signal, sweep)
            f, r = compute_frequency_response(ir, fs=48000)
            sm = smooth_response(r)
            plt.plot(f, sm, label=os.path.basename(take))
        plt.xscale("log")
        plt.ylim(-60, 20)
        plt.grid(True, which="both", linestyle=":", linewidth=0.5)
        plt.title(f"{name} - Anomaly Takes")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Magnitude (dB)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(anomaly_plot, dpi=300)
        # Display the plot
        plt.show()
        plt.close()
        retry = input(f"[📉] Saved anomaly debug plot to {anomaly_plot} \nRetry recording? (y/N): ").strip().lower()
        if retry in ("y", "yes"):
            for file in glob.glob(os.path.join(path, "mic_take_*.wav")) + \
                        glob.glob(os.path.join("output", f"{name}_*", "*.png")) + \
                        glob.glob(os.path.join("output", f"{name}_*", "*.csv")) + \
                        glob.glob(os.path.join("output", f"{name}_*", "*.json")):
                try:
                    os.remove(file)
                except Exception as e:
                    print(f"[!] Failed to delete {file}: {e}")
            for folder in glob.glob(os.path.join("output", f"{name}_*")):
                try:
                    shutil.rmtree(folder)
                except Exception as e:
                    print(f"[!] Failed to remove folder {folder}: {e}")
            time.sleep(0.5)
            return True
    return False

def process_mic_recordings(folder, sweep_path="test_signals/sweep.wav", fs=48000, reference_db=None, smoothing_bins=5, anomaly_threshold_db=6, return_anomalies=False):
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

    if return_anomalies:
        return freqs, smoothed, std_response, normalized, anomalies
    return freqs, smoothed, std_response, normalized


if __name__ == "__main__":
    freqs, avg_db, std_db, _ = process_mic_recordings("test_mic_recordings")
    print(f"Frequencies: {freqs.shape}, Response: {avg_db.shape}")
