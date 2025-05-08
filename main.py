# main.py
import os
from sweep_generator import generate_log_sweep, generate_white_noise, generate_pink_noise
from recorder import record_mic_response
from processor import process_mic_recordings
from plotter import plot_frequency_response


from datetime import datetime

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
            name = input("Enter reference mic name: ").strip()
            path = os.path.join("recordings", f"ref_{name}")
            record_mic_response(path)

        elif choice == "3":
            name = input("Enter test mic name: ").strip()
            path = os.path.join("recordings", name)
            record_mic_response(path)

        elif choice == "4":
            name = input("Enter test mic name to process: ").strip()
            test_path = os.path.join("recordings", name)
            ref_name = input("Enter reference mic name (leave blank for none): ").strip()

            ref_db = None
            if ref_name:
                ref_path = os.path.join("recordings", f"ref_{ref_name}")
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
                f.write("Frequency (Hz);Smoothed Response (dB);Std Dev (dB)")
                for f_hz, db_val, std_val in zip(freqs, smoothed, std):
                    f.write(f"{f_hz:.2f};{db_val:.2f};{std_val:.2f}")
            print(f"[✓] Saved response CSV to {raw_csv_path}")

            if normalized is not None:
                plot_frequency_response(freqs, normalized, label=f"{name} - normalized",
                                        save_path=os.path.join(out_folder, "normalized.png"))
                # Save normalized CSV
                norm_csv_path = os.path.join(out_folder, "normalized.csv")
                with open(norm_csv_path, "w") as f:
                    f.write("Frequency (Hz);Normalized Response (dB)")
                    for f_hz, db_val in zip(freqs, normalized):
                        f.write(f"{f_hz:.2f};{db_val:.2f}")
                print(f"[✓] Saved normalized CSV to {norm_csv_path}")

            # Save metadata
            import json
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
