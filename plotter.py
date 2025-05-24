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
    
def plot_multiple_sweeps(freqs_list, responses_list, labels=None, title="Multiple Sweep Responses", save_path=None, smoothing_bins=50, plot_average=True):
    """
    Plot individual sweep responses with optional smoothing for clarity.
    """
    import matplotlib.pyplot as plt
    from utils import smooth_response

    plt.figure(figsize=(12, 6))
    for i, (freqs, response) in enumerate(zip(freqs_list, responses_list)):
        label = labels[i] if labels else f"Sweep {i+1}"
        smoothed = smooth_response(response, window_bins=smoothing_bins)
        plt.plot(freqs, smoothed, label=label, linewidth=0.8, alpha=0.9)
    if plot_average:
        average_response = np.mean([smooth_response(resp, window_bins=smoothing_bins) for resp in responses_list], axis=0)
        plt.plot(freqs_list[0], average_response, 'k--', label="Average", linewidth=1)
        

    plt.xscale('log')
    plt.xlim(10, 10000)
    plt.ylim(-120, 0)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (dB)")
    plt.title(title)
    plt.grid(True, which="both", linestyle=":", linewidth=0.4)
    plt.xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000], 
               ["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k"])
    plt.legend(fontsize=8)
    plt.tight_layout()

    if save_path:
        # append timestamp yyyymmdd_hhmmss to the filename
        timestamp = np.datetime64('now').astype(str).replace('-', '').replace(':', '').replace('T', '_')
        save_path = save_path.replace(".png", f"_{timestamp}.png")        
        print(f"[✓] Saving individual takes plot to {save_path}")            
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"[✓] Saved individual takes plot to {save_path}")

    plt.show()



if __name__ == "__main__":
    # Dummy example for testing
    freqs = np.logspace(np.log10(20), np.log10(20000), 512)
    mag = -20 + 5 * np.sin(np.log10(freqs))
    plot_frequency_response(freqs, mag)
