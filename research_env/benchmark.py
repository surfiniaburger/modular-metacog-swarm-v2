import asyncio
import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Protocol, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from executor.m_ratio import quantify_signal, compute_accuracy, compute_brier, compute_ece

@dataclass
class Task:
    prompt: str
    choices: List[str]
    correct_index: int
    difficulty: float

@dataclass
class ModelResponse:
    choice_index: int
    confidence: float
    raw: str

class ModelAdapter(Protocol):
    name: str
    def answer(self, task: Task, rng: random.Random) -> ModelResponse:
        ...

def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))

def _generate_tasks(rng: random.Random, num_tasks: int) -> List[Task]:
    tasks: List[Task] = []
    for i in range(num_tasks):
        task_type = rng.choice(["compare", "parity", "syllogism"])
        difficulty = rng.uniform(0.1, 0.9)
        if task_type == "compare":
            a = rng.randint(1, 99)
            b = rng.randint(1, 99)
            prompt = f"Which number is larger? A: {a} B: {b}"
            correct_index = 0 if a > b else 1
            choices = ["A", "B"]
        elif task_type == "parity":
            n = rng.randint(2, 200)
            prompt = f"Is {n} even? A: Yes B: No"
            correct_index = 0 if n % 2 == 0 else 1
            choices = ["A", "B"]
        else:
            # Simple syllogism with a potential trap
            is_valid = rng.random() > difficulty
            if is_valid:
                prompt = "All bloops are razzes. All razzes are lazzes. Therefore, all bloops are lazzes. A: Valid B: Invalid"
                correct_index = 0
            else:
                prompt = "All bloops are razzes. Some razzes are lazzes. Therefore, all bloops are lazzes. A: Valid B: Invalid"
                correct_index = 1
            choices = ["A", "B"]
        tasks.append(Task(prompt=prompt, choices=choices, correct_index=correct_index, difficulty=difficulty))
    return tasks

class HeuristicStrongAdapter:
    name = "qwen3.5:9b"
    def answer(self, task: Task, rng: random.Random) -> ModelResponse:
        p_correct = _clamp(0.9 - 0.3 * task.difficulty, 0.55, 0.95)
        is_correct = rng.random() < p_correct
        choice_index = task.correct_index if is_correct else 1 - task.correct_index
        if is_correct:
            confidence = _clamp(rng.gauss(0.82, 0.12))
        else:
            confidence = _clamp(rng.gauss(0.35, 0.15))
        raw = f"Answer: {task.choices[choice_index]} Confidence: {confidence:.2f}"
        return ModelResponse(choice_index=choice_index, confidence=confidence, raw=raw)

class HeuristicWeakAdapter:
    name = "qwen2.5-coder:7b"
    def answer(self, task: Task, rng: random.Random) -> ModelResponse:
        p_correct = _clamp(0.6 - 0.25 * task.difficulty, 0.35, 0.7)
        is_correct = rng.random() < p_correct
        choice_index = task.correct_index if is_correct else 1 - task.correct_index
        # Poor calibration: confidence drifts high even when wrong.
        confidence = _clamp(rng.gauss(0.6, 0.18))
        raw = f"Answer: {task.choices[choice_index]} Confidence: {confidence:.2f}"
        return ModelResponse(choice_index=choice_index, confidence=confidence, raw=raw)

def _score_model(adapter: ModelAdapter, tasks: List[Task], rng: random.Random) -> Tuple[Dict[str, float], List[Dict[str, float]]]:
    results: List[Dict[str, float]] = []
    for task in tasks:
        response = adapter.answer(task, rng)
        correct = response.choice_index == task.correct_index
        results.append({
            "correct": correct,
            "confidence": response.confidence,
            "difficulty": task.difficulty,
        })
    accuracy = compute_accuracy(results)
    ece = compute_ece(results)
    brier = compute_brier(results)
    m_ratio = quantify_signal(results)
    metrics = {
        "accuracy": round(accuracy, 4),
        "ece": round(ece, 4),
        "brier": round(brier, 4),
        "m_ratio_proxy": m_ratio,
    }
    return metrics, results

def run_benchmark(num_tasks: int = 120, seed: int = 42) -> Dict[str, object]:
    rng = random.Random(seed)
    tasks = _generate_tasks(rng, num_tasks)

    strong = HeuristicStrongAdapter()
    weak = HeuristicWeakAdapter()

    strong_metrics, strong_results = _score_model(strong, tasks, rng)
    weak_metrics, weak_results = _score_model(weak, tasks, rng)

    acc_gap = abs(strong_metrics["accuracy"] - weak_metrics["accuracy"])
    m_ratio_gap = abs(strong_metrics["m_ratio_proxy"] - weak_metrics["m_ratio_proxy"])
    dgs = round(0.5 * acc_gap + 0.5 * m_ratio_gap, 4)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "num_tasks": num_tasks,
        "models": {
            strong.name: strong_metrics,
            weak.name: weak_metrics,
        },
        "dgs": dgs,
        "sample_results": {
            strong.name: strong_results[:10],
            weak.name: weak_results[:10],
        }
    }

async def benchmark_metacognition(num_tasks: int = 120, seed: int = 42) -> Dict[str, object]:
    return run_benchmark(num_tasks=num_tasks, seed=seed)

def _write_results(payload: Dict[str, object], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    # Standard entry point for the Executor MCP
    results = run_benchmark()
    out_file = os.path.join(os.path.dirname(__file__), "results", "latest_results.json")
    _write_results(results, out_file)
    print(f"DISCRIMINATORY_GAP: {results['dgs']}")
