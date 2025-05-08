# recorder.py
import sounddevice as sd
import soundfile as sf
import numpy as np
import os


def record_mic_response(output_folder, sweep_path="test_signals/sweep.wav", fs=48000, channels=1, channel_index=0, repeats=3, device=None):
    """
    Play sweep and record mic response, multiple times. Saves WAV files.
    """
    os.makedirs(output_folder, exist_ok=True)
    sweep, sweep_fs = sf.read(sweep_path)

    if sweep_fs != fs:
        raise ValueError("Sweep sample rate does not match recording sample rate")

    for i in range(repeats):
        print(f"[•] Playing sweep and recording take {i+1}/{repeats}...")

        recording = sd.playrec(sweep, samplerate=fs, channels=channels, dtype='float32', device=device)
        sd.wait()

        if channels == 1 and recording.ndim > 1:
            recording = recording[:, channel_index:channel_index+1]

        output_path = os.path.join(output_folder, f"mic_take_{i+1}.wav")
        sf.write(output_path, recording, fs)
        print(f"[✓] Saved: {output_path}")


if __name__ == "__main__":
    # Test with default device and mono input from channel 0
    record_mic_response("test_mic_recordings", channel_index=0)
