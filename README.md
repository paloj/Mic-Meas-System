# Mic Measurement System

A command-line tool for generating test signals, recording microphone responses, computing frequency responses via deconvolution, and plotting or exporting results. Designed for Windows using WASAPI or ASIO backends via `sounddevice`.

---

## Features

- Generate log-sine sweep (20 Hz → 20 kHz), white noise, pink noise  
- Record 3× sweeps per microphone (reference & device‐under‐test)  
- Deconvolve recordings to obtain impulse responses  
- Compute, smooth, and average frequency responses  
- Detect anomalies and normalize DUT response vs. reference  
- Plot and save results (PNG) and export data (CSV)  
- Export JSON metadata for each session  
- End-to-end system test via `test_all.py`

---

## Dependencies

Install required Python packages:

```bash
pip install numpy scipy sounddevice soundfile matplotlib keyboard
```

---

## Installation

1. Clone or download this repository.  
2. (Optional) Create and activate a Python virtual environment.  
3. Install dependencies (see above).  
4. Optionally edit `settings.ini` to set default devices.

---

## Configuration (`settings.ini`)

```ini
[audio]
backend = WASAPI        ; or ASIO if available
input_device = 2        ; integer index from `sounddevice`
output_device = 26      ; integer index

[sweep]
; Reserved for future parameters (e.g., start/stop frequencies)
```

The CLI will automatically update `backend`, `input_device`, and `output_device` on first run.

---

## Usage

From the project root directory:

```bash
python main.py
```

You will see a menu:

```
🎤 Mic Measurement System
1. Generate test signals
2. Record reference mic
3. Record new mic
4. Process and plot mic response
5. Exit
```

1. **Generate test signals**  
   Produces `test_signals/sweep.wav`, `white_noise.wav`, `pink_noise.wav`.  

2. **Record reference mic**  
   - Prompts for a reference name (e.g. `ref_myMic`)  
   - Selects input/output devices (ASIO/WASAPI)  
   - Chooses channel mode (left/right/center)  
   - Records 3× sweeps into `recordings/ref_<name>/`

3. **Record new mic**  
   Same workflow as reference, saving into `recordings/<name>/`

4. **Process and plot mic response**  
   - Select a reference folder and a DUT folder  
   - Computes average & smoothed dB responses  
   - Normalizes DUT versus reference if provided  
   - Saves plots (`.png`) and CSV exports to `output/<mic>_<timestamp>/`

5. **Exit**  
   Saves any updated device settings back to `settings.ini`

---

## Automated Testing

Run the full system test:

```bash
python test_all.py
```

This script will:  
- Generate test signals  
- Simulate reference & DUT recordings (copies sweep)  
- Process responses, generate plots, export CSV  
- [Optional] Clean up temporary files  

---

## Project Structure

```
.
├── main.py
├── sweep_generator.py
├── recorder.py
├── processor.py
├── plotter.py
├── device_interface.py
├── utils.py
├── test_all.py
├── settings.ini
└── README.md
```

---

## Future Improvements

- Polar-pattern plotting  
- Automated SPL calibration and sensitivity calculation  
- Motorized rotation control for 3D measurements  
- GUI front-end with live visualization  
- Session management and enhanced metadata
