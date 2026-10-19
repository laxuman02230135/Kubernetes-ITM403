"""Export a report figure from one recorded run (requires matplotlib)."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run_directory", type=Path)
args = parser.parse_args()
summary = json.loads((args.run_directory / "summary.json").read_text(encoding="utf-8"))
with (args.run_directory / "timeline.csv").open(encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream))
minutes = [float(row["elapsed_seconds"]) / 60 for row in rows]
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, layout="constrained")
fig.suptitle(f"API autoscaling | student 02230135 | {summary['concurrency']} concurrent clients", fontsize=14)
for axis in axes:
    axis.axvspan(0, summary["load_seconds"] / 60, color="#dbeafe", alpha=0.8)
    axis.grid(axis="y", alpha=0.2)
    axis.spines[["top", "right"]].set_visible(False)
axes[0].step(minutes, [int(row["replicas"]) for row in rows], where="post", color="#1d4ed8", label="Observed replicas")
axes[0].plot(minutes, [int(row["ready"]) for row in rows], ".", color="#15803d", label="Ready replicas")
axes[0].set(ylabel="API Pods", ylim=(0, 7), yticks=range(0, 7))
axes[0].legend(loc="upper right")
cpu_rows = [row for row in rows if row["cpu_percent"]]
axes[1].plot([float(row["elapsed_seconds"]) / 60 for row in cpu_rows],
             [float(row["cpu_percent"]) for row in cpu_rows], "o-", color="#b45309", markersize=3)
axes[1].axhline(50, color="#64748b", linestyle="--", label="HPA target: 50%")
axes[1].set(ylabel="CPU (% of request)", xlabel="Minutes since load started", xlim=(0, max(minutes)), ylim=(0, None))
axes[1].legend(loc="upper right")
fig.supxlabel("Blue shading = load period. Samples every 30 seconds; transitions may occur between samples.", fontsize=9)
output = args.run_directory / "autoscaling.png"
fig.savefig(output, dpi=180)
plt.close(fig)
print(output.resolve())
