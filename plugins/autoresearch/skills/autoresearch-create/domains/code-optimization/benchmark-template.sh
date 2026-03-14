#!/bin/bash
set -euo pipefail

# Pre-check: syntax (< 1 second)
python -c "import ast; ast.parse(open('[MAIN_FILE].py').read())" 2>&1 | head -5

# Correctness check: run once, compare output to reference
ACTUAL=$(python [MAIN_FILE].py [ARGS] 2>&1)
EXPECTED=$(cat [REFERENCE_OUTPUT_FILE] 2>/dev/null || echo "$ACTUAL")
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "CORRECTNESS FAILED: output changed"
  diff <(echo "$EXPECTED") <(echo "$ACTUAL") | head -20
  exit 1
fi

# Timed benchmark — median of 5 runs
TIMES=()
for i in $(seq 1 5); do
  START=$(date +%s%3N)
  python [MAIN_FILE].py [ARGS] > /dev/null 2>&1
  END=$(date +%s%3N)
  TIMES+=($((END - START)))
done

# Sort and take median (index 2 of 5)
SORTED=($(printf '%s\n' "${TIMES[@]}" | sort -n))
MEDIAN=${SORTED[2]}

# Required format
echo "METRIC wall_time_ms=${MEDIAN}"
