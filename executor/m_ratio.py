# executor/m_ratio.py
import math
import logging
from typing import List, Dict

def calculate_m_ratio(meta_d, d):
    """
    M-Ratio = meta-d' / d'
    Measures how efficiently the model's confidence reflects its accuracy.
    Ideal for AGI context: High M-Ratio (1.0) means perfect self-awareness.
    Low M-Ratio (< 0.5) means the model is guessing blindly or hallucinating sensitivity.
    """
    if d == 0:
        return 0
    return round(meta_d / d, 3)

def quantify_signal(results: List[Dict[str, float]]):
    """
    Takes a list of responses and confidence scores to estimate M-Ratio.
    (Simplified prototype for Gen-2 bootstrap)
    """
    correct = [r for r in results if r['correct']]
    incorrect = [r for r in results if not r['correct']]
    
    # We measure 'd' as total accuracy delta
    d = len(correct) / len(results)
    
    # We estimate meta-d as confidence-weighted correct vs confidence-weighted incorrect
    meta_d = sum([r['confidence'] for r in correct]) / (sum([r['confidence'] for r in results]) or 1)
    
    return calculate_m_ratio(meta_d, d)

def compute_accuracy(results: List[Dict[str, float]]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r["correct"]) / len(results)

def compute_brier(results: List[Dict[str, float]]) -> float:
    if not results:
        return 0.0
    return sum((r["confidence"] - (1.0 if r["correct"] else 0.0)) ** 2 for r in results) / len(results)

def compute_ece(results: List[Dict[str, float]], bins: int = 10) -> float:
    """
    Expected Calibration Error for binary correctness with confidence in [0,1].
    """
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

if __name__ == "__main__":
    # Test vector
    test_data = [
        {"correct": True, "confidence": 0.9},
        {"correct": True, "confidence": 0.8},
        {"correct": False, "confidence": 0.2},
    ]
    print(f"Calculated Signal M-Ratio: {quantify_signal(test_data)}")
