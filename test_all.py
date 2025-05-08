# test_all.py
# Script to test all core components of the mic measurement system

import os
from sweep_generator import generate_log_sweep, generate_white_noise, generate_pink_noise
from recorder import record_mic_response
from processor import process_mic_recordings
from plotter import plot_frequency_response
import shutil
from datetime import datetime
import json


def test_system(cleanup=True):
    print("[TEST] Generating test signals...")
    os.makedirs("test_signals", exist_ok=True)
    generate_log_sweep("test_signals/sweep.wav")
    generate_white_noise("test_signals/white_noise.wav")
    generate_pink_noise("test_signals/pink_noise.wav")

    print("[TEST] Simulating reference mic recording...")
    ref_path = "recordings/test_ref"
    os.makedirs(ref_path, exist_ok=True)
    # For testing, copy sweep.wav as fake recordings
    for i in range(1, 4):
        shutil.copy("test_signals/sweep.wav", os.path.join(ref_path, f"mic_take_{i}.wav"))

    print("[TEST] Simulating DUT mic recording...")
    mic_path = "recordings/test_mic"
    os.makedirs(mic_path, exist_ok=True)
    for i in range(1, 4):
        shutil.copy("test_signals/sweep.wav", os.path.join(mic_path, f"mic_take_{i}.wav"))

    print("[TEST] Processing mic and reference...")
    _, ref_db, _, _ = process_mic_recordings(ref_path)
    freqs, smoothed, std, normalized = process_mic_recordings(mic_path, reference_db=ref_db)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_folder = os.path.join("output", f"test_mic_{timestamp}")
    os.makedirs(out_folder, exist_ok=True)

    print("[TEST] Plotting results...")
    plot_frequency_response(freqs, smoothed, std_db=std, label="test_mic",
                            reference_db=ref_db, save_path=os.path.join(out_folder, "response.png"))

    plot_frequency_response(freqs, normalized, label="test_mic - normalized",
                            save_path=os.path.join(out_folder, "normalized.png"))

    with open(os.path.join(out_folder, "response.csv"), "w") as f:
        f.write("Frequency (Hz);Smoothed Response (dB);Std Dev (dB)\n")
        for f_hz, db_val, std_val in zip(freqs, smoothed, std):
            f.write(f"{f_hz:.2f};{db_val:.2f};{std_val:.2f}\n")

    with open(os.path.join(out_folder, "normalized.csv"), "w") as f:
        f.write("Frequency (Hz);Normalized Response (dB)\n")
        for f_hz, db_val in zip(freqs, normalized):
            f.write(f"{f_hz:.2f};{db_val:.2f}\n")

    metadata = {
        "mic_name": "test_mic",
        "timestamp": timestamp,
        "reference_mic": "test_ref",
        "output_folder": out_folder,
        "sweep_file": "test_signals/sweep.wav",
        "sample_rate": 48000,
        "num_sweeps": 3
    }
    with open(os.path.join(out_folder, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[✓] All tests completed. Results saved to {out_folder}")

    if cleanup:
        print("[CLEANUP] Removing temporary test recordings...")
        try:
            shutil.rmtree(ref_path)
            shutil.rmtree(mic_path)
            print("[✓] Cleanup done.")
        except PermissionError as e:
            print(f"[!] Cleanup warning: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run full system test for mic measurement")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep temporary test files")
    args = parser.parse_args()

    test_system(cleanup=not args.no_cleanup)
