#!/bin/bash
# Reset Script for Golden Run v2 (Resilience & Recovery)

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
USE_A2A_BENCHMARK=1 A2A_BENCH_URL=http://localhost:8004 USE_OLLAMA=1 BENCH_LOG_FULL=1 BENCH_NUM_TASKS=40 OLLAMA_TIMEOUT=30 OLLAMA_RETRIES=2 OLLAMA_SLEEP=0.2 ./launch_gen2.sh
