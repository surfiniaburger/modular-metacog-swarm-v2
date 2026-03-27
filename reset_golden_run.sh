#!/bin/bash
# Reset Script for Golden Run v2 (Resilience & Recovery)

# Model Defaults
DEFAULT_BRAIN_MODEL="ollama/qwen3.5:9b"
DEFAULT_HANDS_MODEL="ollama/qwen2.5-coder:3b"
DEFAULT_MODEL_LIST="qwen3.5:9b,qwen2.5-coder:3b"

echo "🔄 Archiving poisoned refusal logs..."
mv research_env/program.md research_env/program_refusal_archive.md

echo "📝 Preparing fresh mission grounding..."
cat <<EOF > research_env/program.md
---
**Session Reset: Golden Run v2 (Resilient) Initiated**
Mission: Extract M-Ratio and Calibration Sensitivity signals via Metacognitive Probing.
Grounding: chandra_packet.json + Fleming & Lau (2014)
---
EOF

echo "🚀 Launching Resilient Swarm..."
USE_A2A_BENCHMARK=1 \
BENCH_EVERY_N=3 \
A2A_BENCH_URL=http://localhost:8004 \
A2A_BENCH_TIMEOUT=900 \
BENCH_RETRIES=2 \
BENCH_SLEEP_SECONDS=3 \
USE_LITELLM=1 \
BENCH_LOG_FULL=0 \
BENCH_NUM_TASKS=20 \
BENCH_PER_MODEL_MAX_SECONDS=60 \
BENCH_SUMMARY_EVERY_N=10 \
BENCH_SUMMARY_ON_END=1 \
BENCH_MIN_ITERATION=2 \
RUN_ITERATIONS=15 \
OLLAMA_TIMEOUT=30 \
OLLAMA_RETRIES=2 \
OLLAMA_SLEEP=0.2 \
BRAIN_MODEL=${BRAIN_MODEL:-$DEFAULT_BRAIN_MODEL} \
HANDS_MODEL=${HANDS_MODEL:-$DEFAULT_HANDS_MODEL} \
CRITIC_MODEL=${CRITIC_MODEL:-$DEFAULT_BRAIN_MODEL} \
MODEL_LIST=${MODEL_LIST:-$DEFAULT_MODEL_LIST} \
BENCH_MODEL_STRONG=${BENCH_MODEL_STRONG:-$DEFAULT_BRAIN_MODEL} \
BENCH_MODEL_WEAK=${BENCH_MODEL_WEAK:-$DEFAULT_HANDS_MODEL} \
./launch_gen2.sh
