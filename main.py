# main.py
import os
import threading
import sys
import keyboard
from datetime import datetime
import json
import configparser
import sounddevice as sd
from sweep_generator import generate_log_sweep, generate_white_noise, generate_pink_noise
from recorder import record_mic_response
from processor import process_mic_recordings
from plotter import plot_frequency_response
from device_interface import list_devices_by_hostapi


def menu():
    n = None  # default sweep count for metadata
    config_path = "settings.ini"
    config = configparser.ConfigParser()
    config.read(config_path)

    if "audio" not in config:
        config["audio"] = {}
    

    hostapis = sd.query_hostapis()
    asio_index = next((i for i, api in enumerate(hostapis) if "ASIO" in api['name'].upper()), None)

    if asio_index is not None:
        print(f"[🎧] Using ASIO backend: {hostapis[asio_index]['name']}")
        sd.default.hostapi = asio_index
        config["audio"]["backend"] = "ASIO"
    else:
        print("[⚠] ASIO backend not found. Using system default.")
        config["audio"]["backend"] = "WASAPI"

    def get_saved_or_prompt_device(key, prompt):
        try:
            saved = int(config["audio"].get(key, ""))
            name = sd.query_devices(saved)["name"]
            print(f"[ℹ] Using saved {prompt.lower()} ({saved}): {name}")
            return saved
        except:
            print(f"[?] Listing devices from host API #{asio_index}...")
            idx = list_devices_by_hostapi(asio_index, prompt=prompt)
            config["audio"][key] = str(idx)
            return idx

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

        elif choice in ["2", "3"]:
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue

            name = input("Enter mic name: ").strip()
            path = os.path.join("recordings", f"ref_{name}" if choice == "2" else name)
            input_device = get_saved_or_prompt_device("input_device", "Select input device")
            output_device = get_saved_or_prompt_device("output_device", "Select output device")

            input_mode = input("Input channel mode (left/right/stereo) [left]: ").strip().lower() or "left"
            output_mode = input("Output channel mode (left/right/stereo) [left]: ").strip().lower() or "left"
            count = input("Number of sweeps [3]: ").strip()
            try:
                n = int(count)
            except:
                n = 3

            record_mic_response(path,
                                input_device=input_device,
                                output_device=output_device,
                                input_channel_mode=input_mode,
                                output_channel_mode=output_mode,
                                repeats=n)

        elif choice == "4":
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

            raw_csv_path = os.path.join(out_folder, "response.csv")
            with open(raw_csv_path, "w") as f:
                f.write("Frequency (Hz);Smoothed Response (dB);Std Dev (dB)\n")
                for f_hz, db_val, std_val in zip(freqs, smoothed, std):
                    f.write(f"{f_hz:.2f};{db_val:.2f};{std_val:.2f}\n")
            print(f"[✓] Saved response CSV to {raw_csv_path}")

            if normalized is not None:
                plot_frequency_response(freqs, normalized, label=f"{name} - normalized",
                                        save_path=os.path.join(out_folder, "normalized.png"))
                norm_csv_path = os.path.join(out_folder, "normalized.csv")
                with open(norm_csv_path, "w") as f:
                    f.write("Frequency (Hz);Normalized Response (dB)\n")
                    for f_hz, db_val in zip(freqs, normalized):
                        f.write(f"{f_hz:.2f};{db_val:.2f}\n")
                print(f"[✓] Saved normalized CSV to {norm_csv_path}")

            meta_path = os.path.join(out_folder, "metadata.json")
            metadata = {
                "mic_name": name,
                "timestamp": timestamp,
                "reference_mic": ref_name if ref_name else None,
                "output_folder": out_folder,
                "sweep_file": "test_signals/sweep.wav",
                "sample_rate": 48000,
                "num_sweeps": n if n is not None else "N/A"
            }
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"[✓] Saved metadata to {meta_path}")

        elif choice == "5":
            break
        else:
            print("Invalid option.")

    with open(config_path, "w") as f:
        config.write(f)


if __name__ == "__main__":
    menu()

    print("[✓] Mic Measurement System exited.")
    sys.exit(0)