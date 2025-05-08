# main.py
import os
from datetime import datetime
import json
from sweep_generator import generate_log_sweep, generate_white_noise, generate_pink_noise
from recorder import record_mic_response
from processor import process_mic_recordings
from plotter import plot_frequency_response
from device_interface import select_device


def menu():
    while True:
        print("\n🎤 Mic Measurement System")
        print("1. Generate test signals")
        print("2. Record reference mic")
        print("3. Record new mic")
        print("4. Process and plot mic response")
        print("5. Exit")
        choice = input("Select option: ")

        if choice == "1":
            os.makedirs("test_signals", exist_ok=True)
            generate_log_sweep("test_signals/sweep.wav")
            generate_white_noise("test_signals/white_noise.wav")
            generate_pink_noise("test_signals/pink_noise.wav")

        elif choice == "2":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter reference mic name: ").strip()
            path = os.path.join("recordings", f"ref_{name}")
            device_index = select_device(prompt="Select input device for reference mic:")
            print("[⚠] If using a multi-channel interface, only channel 1 will be recorded.")
            channel = input("Select input channel (e.g., 1 for mono): ").strip()
            try:
                channel_idx = int(channel) - 1
            except ValueError:
                print("[!] Invalid channel. Defaulting to channel 1.")
                channel_idx = 0
            record_mic_response(path, device=device_index, channels=1, channel_index=channel_idx)

        elif choice == "3":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter test mic name: ").strip()
            path = os.path.join("recordings", name)
            device_index = select_device(prompt="Select input device for test mic:")
            record_mic_response(path, device=device_index)

        elif choice == "4":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter test mic name to process: ").strip()
            test_path = os.path.join("recordings", name)
            if not os.path.exists(test_path):
                print("[!] Test mic folder not found.")
                continue
            ref_name = input("Enter reference mic name (leave blank for none): ").strip()

            ref_db = None
            if ref_name:
                ref_path = os.path.join("recordings", f"ref_{ref_name}")
                if not os.path.exists(ref_path):
                    print("[!] Reference mic folder not found.")
                    continue
                _, ref_db, _, _ = process_mic_recordings(ref_path)

            freqs, smoothed, std, normalized = process_mic_recordings(test_path, reference_db=ref_db)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_folder = os.path.join("output", f"{name}_{timestamp}")
            os.makedirs(out_folder, exist_ok=True)

            plot_frequency_response(freqs, smoothed, std_db=std, label=name,
                                    reference_db=ref_db, save_path=os.path.join(out_folder, "response.png"))

            # Save raw/smoothed CSV
            raw_csv_path = os.path.join(out_folder, "response.csv")
            with open(raw_csv_path, "w") as f:
                f.write("Frequency (Hz);Smoothed Response (dB);Std Dev (dB)\n")
                for f_hz, db_val, std_val in zip(freqs, smoothed, std):
                    f.write(f"{f_hz:.2f};{db_val:.2f};{std_val:.2f}\n")
            print(f"[✓] Saved response CSV to {raw_csv_path}")

            if normalized is not None:
                plot_frequency_response(freqs, normalized, label=f"{name} - normalized",
                                        save_path=os.path.join(out_folder, "normalized.png"))
                # Save normalized CSV
                norm_csv_path = os.path.join(out_folder, "normalized.csv")
                with open(norm_csv_path, "w") as f:
                    f.write("Frequency (Hz);Normalized Response (dB)\n")
                    for f_hz, db_val in zip(freqs, normalized):
                        f.write(f"{f_hz:.2f};{db_val:.2f}\n")
                print(f"[✓] Saved normalized CSV to {norm_csv_path}")

            # Save metadata
            meta_path = os.path.join(out_folder, "metadata.json")
            metadata = {
                "mic_name": name,
                "timestamp": timestamp,
                "reference_mic": ref_name if ref_name else None,
                "output_folder": out_folder,
                "sweep_file": "test_signals/sweep.wav",
                "sample_rate": 48000,
                "num_sweeps": 3
            }
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"[✓] Saved metadata to {meta_path}")

        elif choice == "5":
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    menu()
