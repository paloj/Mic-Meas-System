# sweep_generator.py
import numpy as np
from scipy.signal import chirp
import soundfile as sf
import os


def generate_log_sweep(filename="sweep.wav", duration=10.0, fs=48000, f_start=20.0, f_end=20000.0):
    """
    Generate a logarithmic sine sweep and save to WAV.
    """
    t = np.linspace(0, duration, int(fs * duration))
    sweep = chirp(t, f_start, t[-1], f_end, method='logarithmic')

    # Normalize to -1 to 1 range
    sweep /= np.max(np.abs(sweep))

    # Save
    sf.write(filename, sweep, fs)
    print(f"[✓] Logarithmic sine sweep saved as {filename}")


def generate_white_noise(filename="white_noise.wav", duration=10.0, fs=48000):
    noise = np.random.normal(0, 0.5, int(duration * fs))
    noise /= np.max(np.abs(noise))
    sf.write(filename, noise, fs)
    print(f"[✓] White noise saved as {filename}")


def generate_pink_noise(filename="pink_noise.wav", duration=10.0, fs=48000):
    # Generate pink noise using Voss-McCartney algorithm approximation
    from scipy.signal import lfilter
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    white = np.random.randn(int(duration * fs))
    pink = lfilter(b, a, white)
    pink /= np.max(np.abs(pink))
    sf.write(filename, pink, fs)
    print(f"[✓] Pink noise saved as {filename}")


if __name__ == "__main__":
    os.makedirs("test_signals", exist_ok=True)
    generate_log_sweep("test_signals/sweep.wav")
    generate_white_noise("test_signals/white_noise.wav")
    generate_pink_noise("test_signals/pink_noise.wav")