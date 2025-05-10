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


def handle_anomaly_detection(name, path, anomaly_threshold_db):
    from processor import process_mic_recordings as check_anomalies, compute_frequency_response, deconvolve
    from plotter import plot_frequency_response
    from utils import smooth_response
    import matplotlib.pyplot as plt
    import soundfile as sf
    import glob
    import os
    import shutil
    import time

    freqs, smoothed, std, _, anomalies = check_anomalies(path, return_anomalies=True, anomaly_threshold_db=anomaly_threshold_db)
    if anomalies:
        anomaly_plot = os.path.join("output", f"{name}_anomaly_debug.png")
        sweep, _ = sf.read("test_signals/sweep.wav")
        takes = sorted(glob.glob(os.path.join(path, "mic_take_*.wav")))
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
        print(f"[📉] Saved anomaly debug plot to {anomaly_plot}")

        retry = input(f"[!] Anomaly detected in take(s): {anomalies}Retry recording? (y/N): ").strip().lower()
        if retry == "y":
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

def menu():
    config_path = "settings.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    if "processor" not in config:
        config["processor"] = {}
    anomaly_threshold_db = float(config["processor"].get("anomaly_threshold_db", "6"))
    n = None  # default sweep count for metadata

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
        print("🎤 Mic Measurement System")
        print("1. Record new mic")
        print("2. Record reference mic")
        print("3. Generate test signals")
        print("4. Process and plot mic response")
        print("5. Exit")
        choice = input("Select option: ")
        

        if choice == "1":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue

            name = input("Enter mic name: ").strip()
            path = os.path.join("recordings", name)
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

            # Record 5s of white and pink noise via playback and recording
            from recorder import record_mic_response
            print("[🎧] Playing and recording white noise (5s)...")
            record_mic_response(
                output_folder=path,
                sweep_path="test_signals/white_noise.wav",
                fs=48000,
                input_device=input_device,
                output_device=output_device,
                input_channel_mode=input_mode,
                output_channel_mode=output_mode,
                repeats=1
            )
            os.rename(os.path.join(path, "mic_take_1.wav"), os.path.join(path, "white_noise.wav"))

            print("[🎧] Playing and recording pink noise (5s)...")
            record_mic_response(
                output_folder=path,
                sweep_path="test_signals/pink_noise.wav",
                fs=48000,
                input_device=input_device,
                output_device=output_device,
                input_channel_mode=input_mode,
                output_channel_mode=output_mode,
                repeats=1
            )
            os.rename(os.path.join(path, "mic_take_1.wav"), os.path.join(path, "pink_noise.wav"))

            if handle_anomaly_detection(name, path, anomaly_threshold_db):
                continue

        elif choice == "2":
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

        elif choice == "3":
            os.makedirs("test_signals", exist_ok=True)
            generate_log_sweep("test_signals/sweep.wav")
            generate_white_noise("test_signals/white_noise.wav")
            generate_pink_noise("test_signals/pink_noise.wav")

            # Also record 5s of white and pink noise for future use
            from time import sleep
            import soundfile as sf
            import numpy as np

            print("[🎙] Recording white noise (5s)...")
            white, _ = sf.read("test_signals/white_noise.wav")
            white = white[:240000]  # 5s at 48kHz
            sf.write("test_signals/white_recorded.wav", white, 48000)

            print("[🎙] Recording pink noise (5s)...")
            pink, _ = sf.read("test_signals/pink_noise.wav")
            pink = pink[:240000]  # 5s at 48kHz
            sf.write("test_signals/pink_recorded.wav", pink, 48000)

        elif choice == "4":
            # List available mic recordings
            all_mics = sorted([d for d in os.listdir("recordings") if os.path.isdir(os.path.join("recordings", d))])
            print("Available mic recordings:")
            for i, mic in enumerate(all_mics, 1):
                print(f"{i}. {mic}")

            # Auto-suggest last used mic names from config
            last_test = config.get("audio", "last_test_mic", fallback="")
            last_ref = config.get("audio", "last_ref_mic", fallback="")

            name_input = input(f"Enter test mic name to process (number or name) [default: {last_test}]: ").strip()
            if name_input.isdigit() and 1 <= int(name_input) <= len(all_mics):
                name = all_mics[int(name_input)-1]
            else:
                name = name_input or last_test
            test_path = os.path.join("recordings", name)
            if not os.path.exists(test_path):
                print("[!] Test mic folder not found.")
                continue

            ref_input = input(f"Enter reference mic name (number or name) [default: {last_ref}]: ").strip()
            if ref_input.isdigit() and 1 <= int(ref_input) <= len(all_mics):
                ref_name = all_mics[int(ref_input)-1]
            else:
                ref_name = ref_input or last_ref
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

            # Log to run history
            with open("run_history.log", "a") as log:
                log.write(f"{timestamp} | Test: {name} | Reference: {ref_name} | Output: {out_folder}")
            config["audio"]["last_test_mic"] = name
            config["audio"]["last_ref_mic"] = ref_name

        elif choice == "5":
            break
        else:
            print("Invalid option.")

        config["processor"]["anomaly_threshold_db"] = str(anomaly_threshold_db)
    with open(config_path, "w") as f:
        config.write(f)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("[TEST] Running system tests...")
        # Add test functions here
    else:
        menu()

