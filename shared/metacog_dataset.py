import random
from typing import Dict, List


def generate_metacog_rows(
    n: int = 200,
    seed: int = 42,
    trap_boost: bool = False,
    adversarial_share: float = 0.25,
) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    adversarial_share = max(0.0, min(1.0, float(adversarial_share)))
    if trap_boost:
        adversarial_share = min(0.6, max(adversarial_share, 0.5))

    tiers = ["easy", "medium", "hard", "adversarial"]
    tier_difficulty = {
        "easy": 0.2,
        "medium": 0.5,
        "hard": 0.7,
        "adversarial": 0.9,
    }
    non_adv = ["easy", "medium", "hard"]
    rows: List[Dict[str, object]] = []

    for i in range(n):
        if rng.random() < adversarial_share:
            tier = "adversarial"
        else:
            tier = rng.choice(non_adv)

        if tier == "easy":
            a = rng.randint(1, 99)
            b = rng.randint(1, 99)
            prompt = f"Which number is larger? A: {a} B: {b}"
            answer = "A" if a > b else "B"
            rows.append({
                "prompt": prompt,
                "answer": answer,
                "difficulty": tier_difficulty[tier],
                "tier": tier,
                "trap": "none",
            })
        elif tier == "medium":
            nums = [rng.randint(1, 20) for _ in range(3)]
            sorted_nums = sorted(nums)
            a = sorted_nums
            b = sorted_nums[:]
            rng.shuffle(b)
            if b == a:
                b = a[::-1]
            prompt = (
                "Which ordering is ascending? "
                f"A: {a[0]} < {a[1]} < {a[2]} "
                f"B: {b[0]} < {b[1]} < {b[2]}"
            )
            rows.append({
                "prompt": prompt,
                "answer": "A",
                "difficulty": tier_difficulty[tier],
                "tier": tier,
                "trap": "ordering",
            })
        elif tier == "hard":
            prompt = (
                "If A is left of B and B is left of C, which is true? "
                "A: A is left of C B: C is left of A"
            )
            rows.append({
                "prompt": prompt,
                "answer": "A",
                "difficulty": tier_difficulty[tier],
                "tier": tier,
                "trap": "spatial",
            })
        else:
            a = rng.choice([0.2, 0.3, 0.04, -0.2, -0.5])
            b = rng.choice([0.19, 0.29, 0.4, -0.19, -0.4])
            prompt = f"Which number is larger? A: {a} B: {b}"
            answer = "A" if a > b else "B"
            rows.append({
                "prompt": prompt,
                "answer": answer,
                "difficulty": tier_difficulty[tier],
                "tier": tier,
                "trap": "compare_trap",
            })
    return rows
