# recorder.py
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from device_interface import apply_output_panning, extract_mono_channel
from utils import smooth_response, normalize_response

def record_noise_samples(path, input_device, output_device, input_mode, output_mode):
    print("[🎧] Playing and recording white noise (5s, flush=True)...")
    record_mic_response(
        output_folder=path,
        sweep_path="test_signals/white_noise.wav",
        fs=48000,
        input_device=input_device,
        output_device=output_device,
        input_channel_mode=input_mode,
        output_channel_mode=output_mode,
        repeats=1,
        output_filename="white_noise.wav"
    )

    print("[🎧] Playing and recording pink noise (5s)...")
    record_mic_response(
        output_folder=path,
        sweep_path="test_signals/pink_noise.wav",
        fs=48000,
        input_device=input_device,
        output_device=output_device,
        input_channel_mode=input_mode,
        output_channel_mode=output_mode,
        repeats=1,
        output_filename="pink_noise.wav"
    )

def record_mic_response(output_folder, sweep_path="test_signals/sweep.wav", fs=48000,
                         input_device=None, output_device=None,
                         input_channel_mode="left", output_channel_mode="left",
                         repeats=3, output_filename=None, output_filename_prefix=None):
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

    # Play sweep and record
    for i in range(repeats):
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
            while True:
                sd.sleep(50)
                if cursor[0] >= len(stereo_sweep):
                    break

        if input_channel_mode == "left":
            mono = extract_mono_channel(recording, 0)
        elif input_channel_mode == "right":
            mono = extract_mono_channel(recording, 1)
        else:
            mono = recording  # stereo

        if output_filename:
            output_path = os.path.join(output_folder, output_filename)
        elif output_filename_prefix:
            output_path = os.path.join(output_folder, f"{output_filename_prefix}{i+1}.wav")
        else:
            output_path = os.path.join(output_folder, f"mic_take_{i+1}.wav")

        sf.write(output_path, mono, fs)
        print(f"[✓] Saved: {output_path}")

    print("[✓] Recording completed.")
 