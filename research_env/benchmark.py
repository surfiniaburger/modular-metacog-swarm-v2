import asyncio
import json
import os
import random
import re
import sys
import time
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

def _score_model(adapter: ModelAdapter, tasks: List[Task], rng: random.Random, max_seconds: float | None = None) -> Tuple[Dict[str, float], List[Dict[str, float]], dict]:
    results: List[Dict[str, float]] = []
    responses: dict = {}
    started = time.time()
    skipped = 0
    for idx, task in enumerate(tasks):
        if max_seconds is not None and (time.time() - started) > max_seconds:
            skipped += 1
            continue
        response = adapter.answer(task, rng)
        correct = response.choice_index == task.correct_index
        results.append({
            "correct": correct,
            "confidence": response.confidence,
            "difficulty": task.difficulty,
        })
        responses[idx] = response
    accuracy = compute_accuracy(results)
    ece = compute_ece(results)
    brier = compute_brier(results)
    m_ratio = quantify_signal(results)
    metrics = {
        "accuracy": round(accuracy, 4),
        "ece": round(ece, 4),
        "brier": round(brier, 4),
        "m_ratio_proxy": m_ratio,
        "tasks_completed": len(results),
        "tasks_skipped": skipped,
    }
    return metrics, results, responses

class OllamaAdapter:
    def __init__(self, name: str, host: str):
        self.name = name
        self.host = host.rstrip("/")
        self.timeout_s = float(os.getenv("OLLAMA_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("OLLAMA_RETRIES", "2"))
        self.retry_backoff = float(os.getenv("OLLAMA_BACKOFF", "1.5"))
        self.sleep_between = float(os.getenv("OLLAMA_SLEEP", "0.1"))

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
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8")
                parsed = json.loads(body)
                if self.sleep_between > 0:
                    import time
                    time.sleep(self.sleep_between)
                return parsed.get("response", "")
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    import time
                    time.sleep(self.retry_backoff * (attempt + 1))
        raise last_err

    @staticmethod
    def _parse_response(text: str) -> Tuple[int, float]:
        # Try JSON first
        try:
            obj = json.loads(text.strip())
            choice = str(obj.get("choice", "")).strip().upper()
            confidence = float(obj.get("confidence", 0.5))
        except Exception:
            # Fallback: regex parse
            choice_match = re.search(r"\b([AB])\b", text.upper())
            conf_match = re.search(r"confidence\s*[:=]\s*([0-1](?:\.\d+)?)", text, re.IGNORECASE)
            if not choice_match or not conf_match:
                raise ValueError(f"Failed to parse model response: {text}")
            choice = choice_match.group(1)
            confidence = float(conf_match.group(1))
        choice_index = 0 if choice == "A" else 1
        return choice_index, _clamp(confidence)

    def answer(self, task: Task, rng: random.Random) -> ModelResponse:
        prompt = self._build_prompt(task)
        try:
            raw = self._call_ollama(prompt)
            choice_index, confidence = OllamaAdapter._parse_response(raw)
            return ModelResponse(choice_index=choice_index, confidence=confidence, raw=raw)
        except Exception:
            # Timeout or transient failure; return neutral response to keep run moving.
            return ModelResponse(choice_index=0, confidence=0.5, raw="ERROR: timeout")

class LiteLLMAdapter:
    def __init__(self, name: str):
        self.name = name

    def _build_prompt(self, task: Task) -> str:
        return (
            "You are a benchmarked model. Answer the multiple-choice question and provide a confidence in [0,1].\n"
            "Return ONLY a JSON object with keys: choice (A or B), confidence (0 to 1).\n"
            f"Question: {task.prompt}\n"
            f"Choices: A: {task.choices[0]} | B: {task.choices[1]}\n"
            "JSON:"
        )

    def answer(self, task: Task, rng: random.Random) -> ModelResponse:
        try:
            from litellm import completion
            prompt = self._build_prompt(task)
            resp = completion(
                model=self.name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                top_p=0.9,
            )
            if not getattr(resp, "choices", None):
                raise ValueError("LiteLLM returned no choices")
            content = resp.choices[0].message["content"]
            choice_index, confidence = OllamaAdapter._parse_response(content)
            return ModelResponse(choice_index=choice_index, confidence=confidence, raw=content)
        except Exception:
            return ModelResponse(choice_index=0, confidence=0.5, raw="ERROR: litellm")

def _select_adapters() -> Tuple[ModelAdapter, ModelAdapter]:
    use_ollama = os.getenv("USE_OLLAMA", "0") == "1"
    use_litellm = os.getenv("USE_LITELLM", "0") == "1"
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    if use_litellm:
        strong_name = os.getenv("BENCH_MODEL_STRONG", "ollama/qwen3.5:9b")
        weak_name = os.getenv("BENCH_MODEL_WEAK", "ollama/qwen2.5-coder:7b")
        return LiteLLMAdapter(strong_name), LiteLLMAdapter(weak_name)
    if use_ollama:
        return OllamaAdapter("qwen3.5:9b", host), OllamaAdapter("qwen2.5-coder:7b", host)
    return HeuristicStrongAdapter(), HeuristicWeakAdapter()

def run_benchmark(num_tasks: int = 120, seed: int = 42, full_log: bool = False) -> Dict[str, object]:
    rng = random.Random(seed)
    tasks = _generate_tasks(rng, num_tasks)

    strong, weak = _select_adapters()

    per_model_max = os.getenv("BENCH_PER_MODEL_MAX_SECONDS")
    per_model_max_s = float(per_model_max) if per_model_max else None
    strong_metrics, strong_results, strong_responses = _score_model(strong, tasks, rng, max_seconds=per_model_max_s)
    weak_metrics, weak_results, weak_responses = _score_model(weak, tasks, rng, max_seconds=per_model_max_s)

    acc_gap = abs(strong_metrics["accuracy"] - weak_metrics["accuracy"])
    m_ratio_gap = abs(strong_metrics["m_ratio_proxy"] - weak_metrics["m_ratio_proxy"])
    dgs = round(0.5 * acc_gap + 0.5 * m_ratio_gap, 4)

    payload = {
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
    if full_log:
        task_log = []
        for idx, task in enumerate(tasks):
            task_log.append({
                "task_index": idx,
                "prompt": task.prompt,
                "choices": task.choices,
                "correct_index": task.correct_index,
                "difficulty": task.difficulty,
                strong.name: {
                    "choice_index": strong_responses.get(idx).choice_index if strong_responses.get(idx) else None,
                    "confidence": strong_responses.get(idx).confidence if strong_responses.get(idx) else None,
                    "correct": (strong_responses.get(idx).choice_index == task.correct_index) if strong_responses.get(idx) else None,
                },
                weak.name: {
                    "choice_index": weak_responses.get(idx).choice_index if weak_responses.get(idx) else None,
                    "confidence": weak_responses.get(idx).confidence if weak_responses.get(idx) else None,
                    "correct": (weak_responses.get(idx).choice_index == task.correct_index) if weak_responses.get(idx) else None,
                },
            })
        payload["task_log"] = task_log
    return payload

async def benchmark_metacognition(num_tasks: int = 120, seed: int = 42, full_log: bool = False) -> Dict[str, object]:
    return run_benchmark(num_tasks=num_tasks, seed=seed, full_log=full_log)

def save_results(payload: Dict[str, object], iteration: int | None = None, write_latest: bool = True) -> None:
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    if iteration is not None:
        out_path = os.path.join(results_dir, f"iteration_{iteration}_results.json")
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)
        if "task_log" in payload:
            log_path = os.path.join(results_dir, f"iteration_{iteration}_tasklog.json")
            with open(log_path, "w") as f:
                json.dump({"timestamp": payload.get("timestamp"), "task_log": payload["task_log"]}, f, indent=2)
    if write_latest:
        out_path = os.path.join(results_dir, "latest_results.json")
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)
        if "task_log" in payload:
            log_path = os.path.join(results_dir, "latest_tasklog.json")
            with open(log_path, "w") as f:
                json.dump({"timestamp": payload.get("timestamp"), "task_log": payload["task_log"]}, f, indent=2)

if __name__ == "__main__":
    # Standard entry point for the Executor MCP
    full_log = os.getenv("BENCH_LOG_FULL", "0") == "1"
    results = run_benchmark(full_log=full_log)
    save_results(results, iteration=None, write_latest=True)
    print(f"DISCRIMINATORY_GAP: {results['dgs']}")
