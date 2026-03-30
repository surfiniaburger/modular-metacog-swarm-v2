# --------------------------------------------------------------------------------
# 📚 LEARNING RESOURCES
# Quick Start: https://github.com/Kaggle/kaggle-benchmarks/blob/ci/quick_start.md
# Cookbook:    https://github.com/Kaggle/kaggle-benchmarks/blob/ci/cookbook.md
# --------------------------------------------------------------------------------

# %%
# --------------------------------------------------------------------------------
# KAGGLE SYNC CELL (optional)
# Uncomment to pull latest changes from GitHub when running on Kaggle.
# --------------------------------------------------------------------------------
!git -C modular-metacog-swarm-v2 pull || git clone https://github.com/surfiniaburger/modular-metacog-swarm-v2.git
%cd modular-metacog-swarm-v2

# %%
import math
import os
import random
import sys
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import kaggle_benchmarks as kbench

# %%
# --- Config ---
CONF_BINS = int(os.getenv("BENCH_CONF_BINS", "4"))
SEED = int(os.getenv("BENCH_SEED", "42"))

# %%
@dataclass
class MetacogAnswer:
    choice: str  # "A" or "B"
    confidence_bin: int  # 1..CONF_BINS


def clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def bin_index(confidence: float, bins: int) -> int:
    if bins <= 1:
        return 1
    idx = int(math.ceil(clamp(confidence) * bins))
    return max(1, min(bins, idx))


def bin_to_confidence(bin_val: int, bins: int) -> float:
    return (bin_val - 0.5) / max(1, bins)


# --- Metrics (ECE/Brier/meta-d′ approx) ---
def compute_accuracy(results: List[Dict[str, float]]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r["correct"]) / len(results)


def compute_brier(results: List[Dict[str, float]]) -> float:
    if not results:
        return 0.0
    return sum((r["confidence"] - (1.0 if r["correct"] else 0.0)) ** 2 for r in results) / len(results)


def compute_ece(results: List[Dict[str, float]], bins: int = 10) -> float:
    if not results:
        return 0.0
    bins = max(1, int(bins))
    total = len(results)
    ece = 0.0
    for b in range(bins):
        lower = b / bins
        upper = (b + 1) / bins
        bucket = [r for r in results if lower <= r["confidence"] < upper or (b == bins - 1 and r["confidence"] == 1.0)]
        if not bucket:
            continue
        acc = sum(1 for r in bucket if r["correct"]) / len(bucket)
        conf = sum(r["confidence"] for r in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(acc - conf)
    return ece


def norm_ppf(p: float) -> float:
    # Acklam approximation
    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572]
    c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416]
    plow = 0.02425
    phigh = 1 - plow
    if p <= 0:
        return -float("inf")
    if p >= 1:
        return float("inf")
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def d_prime_from_accuracy(accuracy: float) -> float:
    acc = clamp(float(accuracy), 1e-5, 1 - 1e-5)
    return math.sqrt(2) * norm_ppf(acc)


def type2_roc_auc(results: List[Dict[str, float]], bins: int) -> float:
    if not results:
        return 0.0
    bins = max(1, int(bins))
    correct = [r for r in results if r["correct"]]
    incorrect = [r for r in results if not r["correct"]]
    if not correct or not incorrect:
        return 0.0
    roc = []
    for k in range(1, bins + 1):
        hit = sum(1 for r in correct if r["bin"] >= k) / len(correct)
        fa = sum(1 for r in incorrect if r["bin"] >= k) / len(incorrect)
        roc.append((fa, hit))
    roc = sorted(roc, key=lambda x: x[0])
    if roc[0][0] > 0 or roc[0][1] > 0:
        roc = [(0.0, 0.0)] + roc
    if roc[-1][0] < 1.0 or roc[-1][1] < 1.0:
        roc = roc + [(1.0, 1.0)]
    auc = 0.0
    for i in range(1, len(roc)):
        x0, y0 = roc[i - 1]
        x1, y1 = roc[i]
        auc += (x1 - x0) * (y0 + y1) / 2.0
    return clamp(auc, 0.0, 1.0)


# --------------------------------------------------------------------------------
# STEP 1: DEFINE YOUR TASK + DATASET
# --------------------------------------------------------------------------------

# Procedural dataset generator (difficulty + trap labels).
rows = generate_metacog_rows(n=200, seed=SEED)
tasks_df = pd.DataFrame(rows)


# %%
# The @task decorator turns a standard Python function into a Benchmark task.
# The first parameter must always be `llm` (the model being tested).
@kbench.task(name="metacog_single_item")
def metacog_single_item(llm, prompt: str, answer: str) -> float:
    """
    Returns 1.0 if correct, else 0.0.
    Also enforces structured output with confidence bins.
    """
    response: MetacogAnswer = llm.prompt(
        prompt,
        schema=MetacogAnswer,
    )
    choice = response.choice.strip().upper()
    conf_bin = max(1, min(CONF_BINS, int(response.confidence_bin)))
    return 1.0 if choice == answer else 0.0


# --------------------------------------------------------------------------------
# STEP 2: RUN THE TASK
# We use `kbench.llm` as a placeholder. This allows Kaggle to swap models later.
# --------------------------------------------------------------------------------
# Evaluate on the dataset.
results = metacog_single_item.evaluate(
    llm=[kbench.llm], evaluation_data=tasks_df[["prompt", "answer"]]
)
df = results.as_dataframe()
print(df.head())


# %%
# Optional: compute aggregate accuracy.
accuracy = df["score"].mean()
print("Accuracy:", round(float(accuracy), 4))


# %%
# Full metrics pass (runs the same prompts again to collect confidence bins).
def run_full_metrics(llm, tasks: pd.DataFrame) -> dict:
    items = []
    for _, row in tasks.iterrows():
        prompt = row["prompt"]
        answer = row["answer"]
        response: MetacogAnswer = llm.prompt(prompt, schema=MetacogAnswer)
        choice = response.choice.strip().upper()
        conf_bin = max(1, min(CONF_BINS, int(response.confidence_bin)))
        conf = bin_to_confidence(conf_bin, CONF_BINS)
        items.append({
            "correct": choice == answer,
            "confidence": conf,
            "bin": conf_bin,
        })
    acc = compute_accuracy(items)
    ece = compute_ece(items)
    brier = compute_brier(items)
    auc = type2_roc_auc(items, bins=CONF_BINS)
    meta_d = math.sqrt(2) * norm_ppf(clamp(auc, 1e-5, 1 - 1e-5))
    d_prime = d_prime_from_accuracy(acc)
    m_ratio = meta_d / d_prime if d_prime != 0 else 0.0
    return {
        "accuracy": round(acc, 4),
        "ece": round(ece, 4),
        "brier": round(brier, 4),
        "type2_auc": round(auc, 4),
        "meta_d_prime": round(meta_d, 4),
        "d_prime": round(d_prime, 4),
        "m_ratio": round(m_ratio, 4),
    }


metrics = run_full_metrics(kbench.llm, tasks_df)
print("Full Metrics:", metrics)


# --------------------------------------------------------------------------------
# STEP 3: NEXT STEPS
# 1. Click "Save Task" to publish to the leaderboard.
# 2. Optionally add `%choose` in the final cell for leaderboard selection.
# --------------------------------------------------------------------------------

# In Kaggle, this should be the last cell:
# %choose metacog_single_item
# Ensure repo root is on path when running inside Kaggle.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from shared.metacog_dataset import generate_metacog_rows
