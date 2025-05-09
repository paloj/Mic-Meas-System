
#plotter.py
import matplotlib.pyplot as plt
import numpy as np
import os



def plot_frequency_response(freqs, response_db, std_db=None, label="Mic", reference_db=None, save_path=None):
    """
    Plot and optionally save frequency response graph.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(freqs, response_db, label=label)

    if std_db is not None:
        plt.fill_between(freqs, response_db - std_db, response_db + std_db, alpha=0.2, label=f"{label} ±std")

    if reference_db is not None:
        plt.plot(freqs, reference_db, '--', label="Reference")
        plt.plot(freqs, response_db - reference_db, label="Delta (Mic - Ref)")

    plt.xscale('log')
    plt.xlim(20, 20000)
    plt.ylim(-60, 10)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (dB)")
    plt.title("Frequency Response")
    plt.grid(True, which="both", ls="--")
    plt.legend()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"[✓] Saved plot to {save_path}")

    plt.show()


if __name__ == "__main__":
    # Dummy example for testing
    freqs = np.logspace(np.log10(20), np.log10(20000), 512)
    mag = -20 + 5 * np.sin(np.log10(freqs))
    plot_frequency_response(freqs, mag)
