#!/bin/bash
set -euo pipefail

# Pre-check: syntax check (< 1 second)
python -c "import ast; ast.parse(open('train.py').read())" 2>&1 | head -5

# Run training with fixed budget
START=$(date +%s%3N)
OUTPUT=$(python train.py 2>&1)
EXIT_CODE=$?
END=$(date +%s%3N)
ELAPSED_S=$(( (END - START) / 1000 ))

if [ $EXIT_CODE -ne 0 ]; then
  echo "$OUTPUT" | tail -20
  exit $EXIT_CODE
fi

# Parse metrics from training output
# Adjust these patterns to match what train.py actually outputs
VAL_BPB=$(echo "$OUTPUT" | grep -oP 'val_bpb[=:\s]+\K[\d.]+' | tail -1)
TRAIN_LOSS=$(echo "$OUTPUT" | grep -oP 'train_loss[=:\s]+\K[\d.]+' | tail -1)
TOKENS_PER_SEC=$(echo "$OUTPUT" | grep -oP 'tok/s[=:\s]+\K[\d.]+' | tail -1 || echo "0")

# Required format: METRIC name=value
echo "METRIC val_bpb=${VAL_BPB}"
echo "METRIC train_loss=${TRAIN_LOSS}"
echo "METRIC tokens_per_second=${TOKENS_PER_SEC}"
echo "METRIC elapsed_seconds=${ELAPSED_S}"
