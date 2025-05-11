# main.py
import os
import threading
import sys
import keyboard
from datetime import datetime
import json
import configparser
import sounddevice as sd
from sweep_generator import generate_log_sweep, generate_white_noise, generate_pink_noise, generate_silence
from recorder import record_mic_response, record_noise_samples
from processor import process_mic_recordings, detect_anomalies
from plotter import plot_frequency_response
from device_interface import list_devices_by_hostapi

def get_saved_or_prompt_device(key, prompt, config, asio_index):
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

# MAIN MENU
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

    while True:
        choice = input(f" \
            🎤 Mic Measurement System\n \
            1. Record new mic\n \
            2. Record reference mic\n \
            3. Generate test signals\n \
            4. Process and plot mic response\n \
            5. Exit\n \
            Select option: ")        

        if choice == "1":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter mic name: ").strip()
            record_mic(name, is_reference=False, config=config, asio_index=asio_index, anomaly_threshold_db=anomaly_threshold_db)
        
        elif choice == "2":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter mic name: ").strip()
            record_mic(name, is_reference=True, config=config, asio_index=asio_index, anomaly_threshold_db=anomaly_threshold_db)

          
        elif choice == "3":
            os.makedirs("test_signals", exist_ok=True)
            generate_log_sweep("test_signals/sweep.wav")
            generate_white_noise("test_signals/white_noise.wav")
            generate_pink_noise("test_signals/pink_noise.wav")
            generate_silence("test_signals/silence.wav")

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
            input_device = get_saved_or_prompt_device("input_device", "Select input device", config, asio_index)
            output_device = get_saved_or_prompt_device("output_device", "Select output device", config, asio_index)

            input_mode = "left"  # Default input channel mode
            output_mode = "left"  # Default output channel mode
            metadata = {
                "version": "v0.9-beta",
                "mic_name": name,
                "timestamp": timestamp,
                "reference_mic": ref_name if ref_name else None,
                "output_folder": out_folder,
                "sweep_file": "test_signals/sweep.wav",
                "sample_rate": 48000,
                "num_sweeps": n if n is not None else "N/A",
                "input_device": sd.query_devices(input_device)["name"] if input_device is not None else None,
                "output_device": sd.query_devices(output_device)["name"] if output_device is not None else None,
                "input_channel_mode": input_mode,
                "output_channel_mode": output_mode
            }

            # Optional: Process short sweep response
            short_pattern = os.path.join(test_path, "short_take_*.wav")
            import glob
            if glob.glob(short_pattern):
                freqs_short, smoothed_short, std_short, _ = process_mic_recordings(test_path,
                                                    sweep_path="test_signals/sweep_short.wav",
                                                    anomaly_threshold_db=anomaly_threshold_db,
                                                    smoothing_bins=5)
                short_plot_path = os.path.join(out_folder, "response_short.png")
                plot_frequency_response(freqs_short, smoothed_short, std_db=std_short, label=f"{name} (short)",
                                        save_path=short_plot_path)

                short_csv_path = os.path.join(out_folder, "response_short.csv")
                with open(short_csv_path, "w") as f:
                    f.write("Frequency (Hz);Smoothed Response (dB);Std Dev (dB)")
                    for f_hz, db_val, std_val in zip(freqs_short, smoothed_short, std_short):
                        f.write(f"{f_hz:.2f};{db_val:.2f};{std_val:.2f}")
                print(f"[✓] Saved short sweep CSV to {short_csv_path}")


                
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"[✓] Saved metadata to {meta_path}")

            # Log to run history
            with open("run_history.log", "a") as log:
                log.write(f"{timestamp} | Test: {name} | Reference: {ref_name} | Output: {out_folder} | Version: v0.9-beta")
            config["audio"]["last_test_mic"] = name
            config["audio"]["last_ref_mic"] = ref_name

        elif choice == "5":
            break
        else:
            print("Invalid option.")

        config["processor"]["anomaly_threshold_db"] = str(anomaly_threshold_db)
    with open(config_path, "w") as f:
        config.write(f)


def record_mic(name, is_reference=False, config=None, asio_index=None, anomaly_threshold_db=6):
    prefix = "ref_" if is_reference else ""
    path = os.path.join("recordings", f"{prefix}{name}")
    input_device = get_saved_or_prompt_device("input_device", "Select input device", config, asio_index)
    output_device = get_saved_or_prompt_device("output_device", "Select output device", config, asio_index)

    input_mode = input("Input channel mode (left/right/stereo) [left]: ").strip().lower() or "left"
    output_mode = input("Output channel mode (left/right/stereo) [left]: ").strip().lower() or "left"
    count = input("Number of sweeps [3]: ").strip()
    try:
        n = int(count)
    except:
        n = 3

    # Record ambient noise
    record_mic_response(path,
                        sweep_path="test_signals/silence.wav",
                        input_device=input_device,
                        output_device=output_device,
                        input_channel_mode=input_mode,
                        output_channel_mode=output_mode,
                        repeats=1,
                        output_filename="ambient_noise.wav")

    # Full sweeps
    while True:
        record_mic_response(path,
                            input_device=input_device,
                            output_device=output_device,
                            input_channel_mode=input_mode,
                            output_channel_mode=output_mode,
                            repeats=n)
        anomalies_detected = detect_anomalies(name, path, anomaly_threshold_db)
        if not anomalies_detected:
            break

    # Short sweeps
    while True:
        record_mic_response(path,
                            sweep_path="test_signals/sweep_short.wav",
                            input_device=input_device,
                            output_device=output_device,
                            input_channel_mode=input_mode,
                            output_channel_mode=output_mode,
                            repeats=n,
                            output_filename_prefix="short_take_")
        anomalies_detected = detect_anomalies(name + "_short", path, anomaly_threshold_db,
                                              pattern="short_take_*.wav", sweep_path="test_signals/sweep_short.wav")
        if not anomalies_detected:
            break

    # White and pink noise
    record_noise_samples(path, input_device, output_device, input_mode, output_mode)
    print("[✓] Recording completed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("[TEST] Running system tests...")
        # Add test functions here
    else:
        menu()
