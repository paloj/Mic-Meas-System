
# device_interface.py
import sounddevice as sd
import numpy as np


def list_devices():
    """
    List all available audio devices.
    """
    print("\n[🖥️] Available audio devices:")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        print(f"{i}: {dev['name']} ({'input' if dev['max_input_channels'] > 0 else 'output'})")


def select_device(prompt="Enter device index for recording/playback:"):
    """
    Prompt user to select a device by index.
    """
    list_devices()
    idx = int(input(f"\n{prompt} "))
    sd.default.device = idx
    return idx


def get_device_info():
    """
    Return current input/output device info.
    """
    input_dev, output_dev = sd.default.device
    return sd.query_devices(input_dev), sd.query_devices(output_dev)


def list_devices_by_hostapi(hostapi_index, prompt="Select device:"):
    """
    Filter input/output devices if ASIO not found. Lists only valid choices.
    """
    print(f"[🎚] Listing {prompt.lower()} options...")
    devices = sd.query_devices()
    if "input" in prompt.lower():
        filtered = [(i, d) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
    else:
        filtered = [(i, d) for i, d in enumerate(devices) if d["max_output_channels"] > 0]

    print("[🖥️] Available devices:")
    for idx, dev in filtered:
        print(f"{idx}: {dev['name']} ({'input' if dev['max_input_channels'] > 0 else 'output'})")

    index = int(input(f"{prompt} "))
    return index


def apply_output_panning(stereo_buffer, pan_position):
    """
    Apply panning to stereo sweep signal.
    pan_position: 'left', 'right', or 'center'
    """
    if stereo_buffer.ndim == 1:
        stereo_buffer = np.stack((stereo_buffer, stereo_buffer), axis=-1)
    if pan_position == 'left':
        stereo_buffer[:, 1] = 0  # mute right
    elif pan_position == 'right':
        stereo_buffer[:, 0] = 0  # mute left
    return stereo_buffer


def extract_mono_channel(stereo_input, channel_index):
    """
    Extract left or right from a stereo input recording.
    channel_index: 0 = left, 1 = right
    """
    if stereo_input.ndim == 1:
        return stereo_input.reshape(-1, 1)
    elif stereo_input.shape[1] > channel_index:
        return stereo_input[:, channel_index:channel_index+1]
    else:
        return stereo_input[:, [0]]  # fallback to first

