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
USE_OLLAMA=1 ./launch_gen2.sh
