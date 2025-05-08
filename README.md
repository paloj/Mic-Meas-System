# mic_measurement_system/
# Initial scaffold for DIY microphone test system

# This file is a placeholder that outlines the structure of the system
# Each module contains a TODO header for what it will handle

# main.py
"""
Main CLI menu for the measurement tool.
TODO:
- Display menu with options: record reference, add mic, compare, export
- Route choices to correct modules
"""

# sweep_generator.py
"""
TODO:
- Generate log sine sweep (e.g., 20 Hz to 20 kHz)
- Generate white and pink noise
- Save as WAV for playback
"""

# recorder.py
"""
TODO:
- Interface with sounddevice to play sweep and record input
- Support EVO 16 device selection
- Save 3x sweeps per mic as WAV
"""

# processor.py
"""
TODO:
- Load original sweep and recorded files
- Perform deconvolution to get impulse response
- FFT to get frequency response
- Average 3 sweeps
- Compare to reference mic
- Measure consistency/anomaly detection
- Compute sensitivity (relative SPL)
"""

# plotter.py
"""
TODO:
- Plot raw and normalized frequency response
- Plot polar patterns (future)
- Export plots to PNG
- Export data to CSV
"""

# device_interface.py
"""
TODO:
- List and select audio devices
- Support future motor control (servo/stepper)
"""

# config.py
"""
TODO:
- Store configuration and metadata for each mic
- Manage session data
"""

# utils.py
"""
TODO:
- Helper functions (e.g., smoothing, normalization, conversions)
"""
