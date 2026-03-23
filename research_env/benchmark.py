import asyncio
import json
import os
import random
import re
import sys
import urllib.request
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

class OllamaAdapter:
    def __init__(self, name: str, host: str):
        self.name = name
        self.host = host.rstrip("/")

    def _build_prompt(self, task: Task) -> str:
        return (
            "You are a benchmarked model. Answer the multiple-choice question and provide a confidence in [0,1].\n"
            "Return ONLY a JSON object with keys: choice (A or B), confidence (0 to 1).\n"
            f"Question: {task.prompt}\n"
            f"Choices: A: {task.choices[0]} | B: {task.choices[1]}\n"
            "JSON:"
        )

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
        parsed = json.loads(body)
        return parsed.get("response", "")

    def _parse_response(self, text: str) -> Tuple[int, float]:
        # Try JSON first
        try:
            obj = json.loads(text.strip())
            choice = str(obj.get("choice", "")).strip().upper()
            confidence = float(obj.get("confidence", 0.5))
        except Exception:
            # Fallback: regex parse
            choice_match = re.search(r"\b([AB])\b", text.upper())
            conf_match = re.search(r"confidence\s*[:=]\s*([0-1](?:\.\d+)?)", text, re.IGNORECASE)
            choice = choice_match.group(1) if choice_match else "A"
            confidence = float(conf_match.group(1)) if conf_match else 0.5
        choice_index = 0 if choice == "A" else 1
        return choice_index, _clamp(confidence)

    def answer(self, task: Task, rng: random.Random) -> ModelResponse:
        prompt = self._build_prompt(task)
        raw = self._call_ollama(prompt)
        choice_index, confidence = self._parse_response(raw)
        return ModelResponse(choice_index=choice_index, confidence=confidence, raw=raw)

def _select_adapters() -> Tuple[ModelAdapter, ModelAdapter]:
    use_ollama = os.getenv("USE_OLLAMA", "0") == "1"
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    if use_ollama:
        return OllamaAdapter("qwen3.5:9b", host), OllamaAdapter("qwen2.5-coder:7b", host)
    return HeuristicStrongAdapter(), HeuristicWeakAdapter()

def run_benchmark(num_tasks: int = 120, seed: int = 42) -> Dict[str, object]:
    rng = random.Random(seed)
    tasks = _generate_tasks(rng, num_tasks)

    strong, weak = _select_adapters()

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
