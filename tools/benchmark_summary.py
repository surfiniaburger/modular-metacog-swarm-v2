import json
import os
from statistics import mean, pstdev

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "research_env", "results")

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

def main():
    entries = load_results()
    summary = summarize(entries)
    if not summary:
        print("No benchmark results found.")
        return

    print("Benchmark Summary")
    print(f"Count: {summary['count']}")
    print(f"Mean DGS: {summary['mean_dgs']}")
    print(f"Stdev DGS: {summary['stdev_dgs']}")
    print(f"CV: {summary['cv']}")
    print(f"Signal Quality: {summary['signal_quality']}")
    print("\nPer-iteration DGS:")
    for name, val in summary["values"]:
        print(f"  {name}: {val}")

if __name__ == "__main__":
    main()
