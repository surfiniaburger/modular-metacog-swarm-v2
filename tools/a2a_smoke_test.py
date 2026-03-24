import asyncio
import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from med_safety_gym.messenger import send_message

async def main():
    url = os.getenv("A2A_BENCH_URL", "http://localhost:8004")
    timeout = int(os.getenv("A2A_BENCH_TIMEOUT", "600"))
    payload = json.dumps({
        "num_tasks": 3,
        "seed": 42,
        "full_log": False,
        "iteration": 0
    })
    resp = await send_message(payload, url, timeout=timeout)
    print(resp.get("response", ""))

if __name__ == "__main__":
    asyncio.run(main())
