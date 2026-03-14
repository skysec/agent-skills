#!/bin/bash
set -euo pipefail

# Safety check: ensure we're running in authorized/isolated environment
# Adjust this check to your specific authorization context
if [ ! -f ".autoresearch-authorized" ]; then
  echo "ERROR: .autoresearch-authorized file not found. Confirm authorization before running."
  exit 1
fi

# Run evaluation against held-out set (NEVER tune on eval_set/)
RESULTS=$(python run_eval.py --eval-set eval_set/ --seed 42 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "$RESULTS" | tail -20
  exit $EXIT_CODE
fi

# Parse metrics (adjust grep patterns to match your output format)
DETECTION_RATE=$(echo "$RESULTS" | grep -oP 'detection_rate[=:\s]+\K[\d.]+' | tail -1)
FALSE_POS_RATE=$(echo "$RESULTS" | grep -oP 'false_positive_rate[=:\s]+\K[\d.]+' | tail -1)
F1=$(echo "$RESULTS" | grep -oP 'f1[=:\s]+\K[\d.]+' | tail -1 || echo "0")

# Required format
echo "METRIC detection_rate=${DETECTION_RATE}"
echo "METRIC false_positive_rate=${FALSE_POS_RATE}"
echo "METRIC f1_score=${F1}"
