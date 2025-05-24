# main.py
import os
import sys
from datetime import datetime
import json
import soundfile as sf
import glob
import configparser
import sounddevice as sd
from sweep_generator import generate_log_sweep, generate_white_noise, generate_pink_noise, generate_silence
from recorder import record_mic_response, record_noise_samples
from processor import process_mic_recordings, detect_anomalies
from plotter import plot_frequency_response
from device_interface import list_devices_by_hostapi

# Get defaults from config
config_path = "settings.ini"
config = configparser.ConfigParser()
config.read(config_path)
samplerate = config["audio"].getint("sample_rate", 48000)
default_volume=config["audio"].getfloat("default_volume", 0.1)
# Default input/output modes (left/right/stereo) can be overridden in config
input_mode = config["audio"].get("input_mode", "left").strip().lower()
output_mode = config["audio"].get("output_mode", "left").strip().lower()

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
        
    # Print default volume and samplerate.
    print(f"[ℹ] Default volume level: {default_volume:.2f}")
    print(f"[ℹ] Sample rate: {samplerate} Hz")

    while True:
        # build a clean prompt string without leading spaces
        menu_prompt = (
            "\n🎤 Mic Measurement System\n"
            "1. Record new mic\n"
            "2. Record reference mic\n"
            "3. Generate test signals\n"
            "4. Process and plot mic response\n"
            "5. Quick test\n"
            "6. Exit\n"
            "Select option: "
        )
        choice = input(menu_prompt).strip()

        if choice == "1":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter mic name: ").strip()
            menu_1_2_record_mic(name, is_reference=False, config=config, asio_index=asio_index, anomaly_threshold_db=anomaly_threshold_db)
        
        elif choice == "2":
            if not os.path.exists("test_signals/sweep.wav"):
                print("[!] Sweep file missing. Please generate test signals first.")
                continue
            name = input("Enter mic name: ").strip()
            menu_1_2_record_mic(name, is_reference=True, config=config, asio_index=asio_index, anomaly_threshold_db=anomaly_threshold_db)

          
        elif choice == "3":
            menu_3_generate_signals()
            print("[✓] Test signals generated.")

        elif choice == "4":
            menu_4_compare_mic_responses(config, asio_index, anomaly_threshold_db, n=n)
            
        elif choice == "5":
            menu_5_quick_test(config, asio_index, anomaly_threshold_db)
            print("[✓] Quick test completed.")

        elif choice == "6":
            break
        else:
            print("Invalid option.")

        config["processor"]["anomaly_threshold_db"] = str(anomaly_threshold_db)
    with open(config_path, "w") as f:
        config.write(f)


def menu_1_2_record_mic(name, is_reference=False, config=None, asio_index=None, anomaly_threshold_db=6):
    prefix = "ref_" if is_reference else ""
    path = os.path.join("recordings", f"{prefix}{name}")
    input_device = get_saved_or_prompt_device("input_device", "Select input device", config, asio_index)
    output_device = get_saved_or_prompt_device("output_device", "Select output device", config, asio_index)
    count = input("Number of sweeps [3]: ").strip()
    try:
        n = int(count)
    except:
        n = 3

    # Record ambient noise
    record_mic_response(path,
                        sweep_path="test_signals/silence.wav",
                        fs=samplerate,
                        input_device=input_device,
                        output_device=output_device,
                        input_channel_mode=input_mode,
                        output_channel_mode=output_mode,
                        repeats=1,
                        output_filename="ambient_noise.wav",
                        volume=default_volume)  # Use default volume from config

    # Full sweeps
    while True:
        record_mic_response(path,
                            fs=samplerate,
                            input_device=input_device,
                            output_device=output_device,
                            input_channel_mode=input_mode,
                            output_channel_mode=output_mode,
                            repeats=n,
                            volume=default_volume)  # Use default volume from config)
        anomalies_detected = detect_anomalies(name, path, anomaly_threshold_db)
        if not anomalies_detected:
            break

    # Short sweeps
    while True:
        record_mic_response(path,
                            sweep_path="test_signals/sweep_short.wav",
                            fs=samplerate,
                            input_device=input_device,
                            output_device=output_device,
                            input_channel_mode=input_mode,
                            output_channel_mode=output_mode,
                            repeats=n,
                            output_filename_prefix="short_take_",
                            volume=default_volume)
        anomalies_detected = detect_anomalies(name + "_short", path, anomaly_threshold_db,
                                              pattern="short_take_*.wav", sweep_path="test_signals/sweep_short.wav")
        if not anomalies_detected:
            break

    # White and pink noise
    record_noise_samples(path, input_device, output_device, input_mode, output_mode)
    print("[✓] Recording completed.")


def menu_3_generate_signals():
    os.makedirs("test_signals", exist_ok=True)
    #Generate 10 second log sweep
    generate_log_sweep("test_signals/sweep.wav")
    # Generate 1 second short sweep
    generate_log_sweep("test_signals/sweep_short.wav", duration=2.5)
    generate_white_noise("test_signals/white_noise.wav")
    generate_pink_noise("test_signals/pink_noise.wav")
    generate_silence("test_signals/silence.wav")

    # Also record 5s of white and pink noise for future use
    print("[🎙] Recording white noise (5s)...")
    white, _ = sf.read("test_signals/white_noise.wav")
    white = white[:240000]  # 5s at 48kHz
    sf.write("test_signals/white_recorded.wav", white, samplerate)

    print("[🎙] Recording pink noise (5s)...")
    pink, _ = sf.read("test_signals/pink_noise.wav")
    pink = pink[:240000]  # 5s at 48kHz
    sf.write("test_signals/pink_recorded.wav", pink, samplerate)
    
    
def menu_4_compare_mic_responses(config, asio_index, anomaly_threshold_db, n=None):
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
        return

    ref_input = input(f"Enter reference mic name (number or name) [default: {last_ref}]: ").strip()
    # first decide on the raw ref_name
    if ref_input.isdigit() and 1 <= int(ref_input) <= len(all_mics):
        ref_name = all_mics[int(ref_input) - 1]
    else:
        ref_name = ref_input or last_ref

    # now strip any leading “ref_” and build the actual folder
    clean = ref_name.removeprefix("ref_")
    ref_folder = f"ref_{clean}"
    ref_path = os.path.join("recordings", ref_folder)

    ref_db = None
    if ref_name:
        if not os.path.exists(ref_path):
            print("[!] Reference mic folder not found.")
            return

    freqs, smoothed, std, normalized = process_mic_recordings(test_path, reference_db=ref_db)

    if ref_name and ref_db is not None:
        ref_plot_path = os.path.join(out_folder, "reference.png")
        plot_frequency_response(freqs, ref_db, label=f"{ref_name} (reference)", save_path=ref_plot_path)

        ref_csv_path = os.path.join(out_folder, "reference.csv")
        with open(ref_csv_path, "w") as f:
            f.write("Frequency (Hz);Reference Response (dB)")
            for f_hz, db_val in zip(freqs, ref_db):
                f.write(f"{f_hz:.2f};{db_val:.2f}")
        print(f"[✓] Saved reference CSV to {ref_csv_path}")

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

    metadata = {
        "version": "v0.9-beta",
        "mic_name": name,
        "timestamp": timestamp,
        "reference_mic": ref_name if ref_name else None,
        "output_folder": out_folder,
        "sweep_file": "test_signals/sweep.wav",
        "sample_rate": samplerate,
        "num_sweeps": n if n is not None else "N/A",
        "input_device": sd.query_devices(input_device)["name"] if input_device is not None else None,
        "output_device": sd.query_devices(output_device)["name"] if output_device is not None else None,
        "input_channel_mode": input_mode,
        "output_channel_mode": output_mode
    }

    # Optional: Process short sweep response
    short_pattern = os.path.join(test_path, "short_take_*.wav")
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
    
    
def menu_5_quick_test(config, asio_index, anomaly_threshold_db):
    print("[🎧]Quick test mode selected.")
    input_device = get_saved_or_prompt_device("input_device", "Select input device", config, asio_index)
    output_device = get_saved_or_prompt_device("output_device", "Select output device", config, asio_index)

    path = "quick_test"
    os.makedirs(path, exist_ok=True)
    print("[🎧] Playing and recording log sweep (1s) x 3...")
    
    record_mic_response(
        output_folder=path,
        sweep_path="test_signals/sweep_short.wav",
        fs=samplerate,
        input_device=input_device,
        output_device=output_device,
        input_channel_mode=input_mode,
        output_channel_mode=output_mode,
        repeats=5,
        output_filename_prefix="quick_take_",
        volume=default_volume  # Use default volume from config
    )
    # Load and plot each quick_take individually
    from processor import deconvolve, compute_frequency_response
    from plotter import plot_multiple_sweeps

    sweep, _ = sf.read("test_signals/sweep_short.wav")
    takes = sorted(glob.glob("quick_test/quick_take_*.wav"))
    freqs_list, responses_list = [], []

    for file in takes:
        data, _ = sf.read(file)
        signal = data[:, 0] if data.ndim > 1 else data
        ir = deconvolve(signal, sweep)
        freqs, mag = compute_frequency_response(ir, fs=48000)
        freqs_list.append(freqs)
        responses_list.append(mag)

    plot_multiple_sweeps(
        freqs_list, responses_list, 
        labels=[os.path.basename(f) for f in takes],
        title="Quick Test - Individual Sweeps",
        save_path="quick_test/quick_individual_plot.png",
        smoothing_mode="octave",
        octave_fraction=3
    )

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("[TEST] Running system tests...")
        # Add test functions here
    else:
        menu()