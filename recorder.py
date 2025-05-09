
# recorder.py
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from device_interface import apply_output_panning, extract_mono_channel

def record_mic_response(output_folder, sweep_path="test_signals/sweep.wav", fs=48000,
                         input_device=None, output_device=None,
                         input_channel_mode="left", output_channel_mode="left",
                         repeats=3):
    # Check for incompatible device host APIs
    in_info = sd.query_devices(input_device)
    out_info = sd.query_devices(output_device)
    if in_info['hostapi'] != out_info['hostapi']:
        raise ValueError(f"Incompatible devices: input '{in_info['name']}' and output '{out_info['name']}' use different host APIs.")
    """
    Play sweep and record mic response using separate input/output devices.
    Applies channel selection and output panning. Saves mono WAVs.
    """
    os.makedirs(output_folder, exist_ok=True)
    sweep, sweep_fs = sf.read(sweep_path)

    sweep *= 0.8  # default volume if not overridden externally

    if output_channel_mode == "left":
        stereo_sweep = apply_output_panning(sweep, 'left')
    elif output_channel_mode == "right":
        stereo_sweep = apply_output_panning(sweep, 'right')
    else:
        stereo_sweep = apply_output_panning(sweep, 'center')

    if sweep_fs != fs:
        raise ValueError("Sweep sample rate does not match recording sample rate")

    stop_requested = threading.Event()

    def listen_for_quit():
        print("[↩] Press 'q' + Enter to stop recording...")
        while not stop_requested.is_set():
            try:
                if input().strip().lower() == 'q':
                    stop_requested.set()
                    print("[✋] Quit signal received. Stopping immediately.")
                    break
            except EOFError:
                pass

    quit_thread = threading.Thread(target=listen_for_quit, daemon=True)
    quit_thread.start()

    for i in range(repeats):
        if stop_requested.is_set():
            break
        print(f"[•] Playing sweep and recording take {i+1}/{repeats}...")

        recording = np.zeros((len(sweep), 2), dtype=np.float32)

        cursor = [0]  # mutable cursor to track playback

        def callback(indata, outdata, frames, time, status):
            if status:
                print("[!] Stream warning:", status)

            start = cursor[0]
            end = start + frames
            remaining = len(stereo_sweep) - start

            if remaining >= frames:
                outdata[:frames, :] = stereo_sweep[start:end]
            elif remaining > 0:
                outdata[:remaining, :] = stereo_sweep[start:]
                outdata[remaining:, :] = 0
            else:
                outdata[:, :] = 0

            if end <= len(recording):
                recording[start:end, :] = indata[:frames, :]
            else:
                available = len(recording) - start
                if available > 0:
                    recording[start:, :] = indata[:available, :]

            cursor[0] += frames

        with sd.Stream(samplerate=fs,
                       blocksize=1024,
                       dtype='float32',
                       channels=(2, 2),  # 2 in, 2 out (stereo)
                       device=(input_device, output_device),
                       callback=callback):
            while not stop_requested.is_set():
                sd.sleep(50)
                if cursor[0] >= len(stereo_sweep):
                    break

        if input_channel_mode == "left":
            mono = extract_mono_channel(recording, 0)
        elif input_channel_mode == "right":
            mono = extract_mono_channel(recording, 1)
        else:
            mono = recording  # stereo

        output_path = os.path.join(output_folder, f"mic_take_{i+1}.wav")
        sf.write(output_path, mono, fs)
        print(f"[✓] Saved: {output_path}")

    print("[✓] Recording completed.")
    quit_thread.join()
