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

    from matplotlib.ticker import FixedLocator, FixedFormatter

    plt.xscale('log')
    plt.gca().xaxis.set_major_locator(FixedLocator([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]))
    plt.gca().xaxis.set_major_formatter(FixedFormatter(["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k"]))
    plt.xlim(20, 20000)
    plt.ylim(-60, 20)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (dB)")
    plt.title("Frequency Response")
    plt.grid(True, which="major", ls="--", linewidth=0.6)
    plt.grid(True, which="minor", ls=":", linewidth=0.4)
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
