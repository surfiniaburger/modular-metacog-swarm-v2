import asyncio
import logging
import json
import os
from agent.mediator import ResearchMediator
from shared.hub_client import HubClient
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types
from med_safety_gym.messenger import send_message

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

async def main():
    logger.info("Modular Research Loop starting...")
    
    # 1. Initialize Observability Hub Client
    hub = HubClient(base_url="http://localhost:8000")
    
    # 2. Initialize the Meta-Mediator (The Agent)
    mediator = ResearchMediator()
    
    # 3. Initialize ADK Services for the Runner
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    
    # 4. Initialize the Sovereign Runner
    runner = Runner(
        app_name="ModularResearchSwarm",
        agent=mediator,
        session_service=session_service,
        memory_service=memory_service,
        auto_create_session=True
    )
    
    # 5. Iteration Loop
    pending_bench_tasks = []

    async def fire_a2a_benchmark(iteration: int):
        bench_url = os.getenv("A2A_BENCH_URL", "http://localhost:8004")
        bench_tasks = int(os.getenv("BENCH_NUM_TASKS", "10"))
        bench_seed = int(os.getenv("BENCH_SEED", "42"))
        bench_full_log = os.getenv("BENCH_LOG_FULL", "0") == "1"
        bench_timeout = int(os.getenv("A2A_BENCH_TIMEOUT", "600"))
        request_payload = json.dumps({
            "num_tasks": bench_tasks,
            "seed": bench_seed,
            "full_log": bench_full_log,
            "iteration": iteration
        })
        try:
            response = await send_message(
                message=request_payload,
                base_url=bench_url,
                timeout=bench_timeout,
            )
            await hub.log_event("BENCHMARK_A2A", response.get("response", ""))
        except Exception as e:
            logger.error(f"A2A benchmark failed: {e}")
            await hub.log_event("BENCHMARK_A2A_ERROR", str(e))

    for i in range(1, 16):
        logger.info(f"--- Iteration {i} ---")
        try:
            # Kick off the Mediator via runner.run_async
            # This handles all InvocationContext creation internally.
            async for event in runner.run_async(
                user_id="surfiniaburger",
                session_id="research_run_01",
                new_message=types.Content(role="user", parts=[types.Part(text=f"Start research iteration {i}.")])
            ):
                if event.content:
                    logger.info(f"Mediator Output: {event.content}")
                    await hub.log_event("MEDIATOR_PULSE", str(event.content))
                    
        except Exception as e:
            logger.error(f"Iteration {i} failed: {e}")
            await hub.log_event("ERROR", str(e))

        # Optional A2A benchmark every N iterations (fire-and-forget)
        if os.getenv("USE_A2A_BENCHMARK", "0") == "1":
            every_n = int(os.getenv("BENCH_EVERY_N", "3"))
            if i % every_n == 0:
                task = asyncio.create_task(fire_a2a_benchmark(i))
                pending_bench_tasks.append(task)
                # Clean up finished tasks to avoid growth
                pending_bench_tasks[:] = [t for t in pending_bench_tasks if not t.done()]
        
        await asyncio.sleep(5)  # Cooldown between cognitive cycles

if __name__ == "__main__":
    asyncio.run(main())
