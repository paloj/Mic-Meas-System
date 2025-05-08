import sounddevice as sd


def list_devices():
    """
    List all available audio devices.
    """
    print("[🖥️] Available audio devices:")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        print(f"{i}: {dev['name']} ({'input' if dev['max_input_channels'] > 0 else 'output'})")


def select_device(prompt="Enter device index for recording/playback:"):
    """
    Prompt user to select a device by index.
    """
    list_devices()
    idx = int(input(f"{prompt} "))
    sd.default.device = idx
    return idx


def get_device_info():
    """
    Return current input/output device info.
    """
    input_dev, output_dev = sd.default.device
    return sd.query_devices(input_dev), sd.query_devices(output_dev)


if __name__ == "__main__":
    list_devices()
    idx = select_device()
    print(f"Selected device index: {idx}")