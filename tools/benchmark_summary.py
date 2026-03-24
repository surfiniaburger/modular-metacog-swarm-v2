import json
import os
from statistics import mean, pstdev

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "research_env", "results")
SUMMARY_JSON = os.path.join(RESULTS_DIR, "summary.json")
SUMMARY_PNG = os.path.join(RESULTS_DIR, "summary.png")
SUMMARY_TXT = os.path.join(RESULTS_DIR, "summary.txt")

def load_results():
    entries = []
    if not os.path.isdir(RESULTS_DIR):
        return entries
    for name in os.listdir(RESULTS_DIR):
        if name.startswith("iteration_") and name.endswith("_results.json"):
            path = os.path.join(RESULTS_DIR, name)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                entries.append((name, data))
            except Exception:
                pass
    return sorted(entries, key=lambda x: x[0])

def summarize(entries):
    dgs_values = []
    for name, data in entries:
        dgs = data.get("dgs")
        if isinstance(dgs, (int, float)):
            dgs_values.append((name, float(dgs)))
    if not dgs_values:
        return None

    values = [v for _, v in dgs_values]
    avg = mean(values)
    sd = pstdev(values) if len(values) > 1 else 0.0
    cv = (sd / avg) if avg != 0 else float("inf")

    if len(values) < 3:
        signal = "insufficient_samples"
    elif cv < 0.2:
        signal = "clear"
    elif cv < 0.4:
        signal = "moderate"
    else:
        signal = "muffled"

    return {
        "count": len(values),
        "mean_dgs": round(avg, 4),
        "stdev_dgs": round(sd, 4),
        "cv": round(cv, 4) if cv != float("inf") else "inf",
        "signal_quality": signal,
        "values": dgs_values,
    }

def write_summary_outputs():
    entries = load_results()
    summary = summarize(entries)
    if not summary:
        return None

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    lines = []
    lines.append("Benchmark Summary")
    lines.append(f"Count: {summary['count']}")
    lines.append(f"Mean DGS: {summary['mean_dgs']}")
    lines.append(f"Stdev DGS: {summary['stdev_dgs']}")
    lines.append(f"CV: {summary['cv']}")
    lines.append(f"Signal Quality: {summary['signal_quality']}")
    lines.append("")
    lines.append("Per-iteration DGS:")
    for name, val in summary["values"]:
        lines.append(f"{name}: {val}")
    with open(SUMMARY_TXT, "w") as f:
        f.write("\n".join(lines))

    # Optional plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        xs = list(range(1, len(summary["values"]) + 1))
        ys = [v for _, v in summary["values"]]
        plt.figure(figsize=(6, 3))
        plt.plot(xs, ys, marker="o")
        plt.title("DGS Trend")
        plt.xlabel("Iteration")
        plt.ylabel("DGS")
        plt.tight_layout()
        plt.savefig(SUMMARY_PNG)
        plt.close()
    except Exception:
        pass

    return summary

def main():
    summary = write_summary_outputs()
    if not summary:
        print("No benchmark results found.")
        return
    print("Benchmark Summary")
    print(f"Count: {summary['count']}")
    print(f"Mean DGS: {summary['mean_dgs']}")
    print(f"Stdev DGS: {summary['stdev_dgs']}")
    print(f"CV: {summary['cv']}")
    print(f"Signal Quality: {summary['signal_quality']}")
    print(f"Wrote: {SUMMARY_JSON}")
    if os.path.exists(SUMMARY_PNG):
        print(f"Wrote: {SUMMARY_PNG}")

if __name__ == "__main__":
    main()
