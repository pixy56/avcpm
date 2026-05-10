#!/usr/bin/env bash
# timed-run.sh — Time a command and log the result.
# Usage: timed-run.sh <operation-name> <command...>
#
# Logs to both CRON_LOG.md and PERFORMANCE.md

set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
LEARNINGS_DIR="${WORKSPACE}/.learnings"
CRON_LOG="${LEARNINGS_DIR}/CRON_LOG.md"
PERF_LOG="${LEARNINGS_DIR}/PERFORMANCE.md"

if [ $# -lt 2 ]; then
    echo "Usage: $(basename "$0") <operation-name> <command...>"
    exit 1
fi

OPERATION="$1"
shift

# Sanitize operation name for markdown
OPERATION_CLEAN="${OPERATION//|/\|}"

START_TIME=$(date +%s)
START_HUMAN=$(date -Iseconds)

echo "[${START_HUMAN}] [TIMED] ${OPERATION_CLEAN}: starting..."

# Run the command, capturing exit status
set +e
"$@"
EXIT_CODE=$?
set -e

END_TIME=$(date +%s)
END_HUMAN=$(date -Iseconds)
DURATION=$((END_TIME - START_TIME))

echo "[${END_HUMAN}] [TIMED] ${OPERATION_CLEAN}: ${DURATION}s (exit=${EXIT_CODE})"

# Append to CRON_LOG.md
{
    echo ""
    echo "## ${START_HUMAN} — ${OPERATION_CLEAN}"
    echo "- **Command:** \`$*\`"
    echo "- **Duration:** ${DURATION}s"
    echo "- **Exit code:** ${EXIT_CODE}"
} >> "${CRON_LOG}"

# Append/update PERFORMANCE.md entry
# If the table already has an entry for this operation, update Last Run + Trend.
# Otherwise, append a new row with baseline = duration.

tmpfile=$(mktemp)

if grep -q "^| ${OPERATION_CLEAN} |" "${PERF_LOG}" 2>/dev/null; then
    # Update existing row
    awk -v op="${OPERATION_CLEAN}" \
        -v dur="${DURATION}" \
        -v threshold="${THRESHOLD:-}" \
        'BEGIN {FS=" | "; OFS=" | "}
        {
            # Each line: | Operation | Baseline | Last Run | Trend | Alert Threshold |
            if ($2 == " " op " ") {
                baseline=$4
                last=$6
                # Simple trend logic
                gsub(/ /, "", baseline)
                gsub(/ /, "", last)
                gsub(/ /, "", dur)
                if (dur > last + 5) trend="worsening"
                else if (dur < last - 5) trend="improving"
                else trend="stable"
                print "| " op " | " baseline " | " dur "s | " trend " | " ($10 != "" ? $10 : (threshold != "" ? ">" threshold : ">300s")) " |"
            } else {
                print
            }
        }' "${PERF_LOG}" > "${tmpfile}" && mv "${tmpfile}" "${PERF_LOG}"
else
    # Append new row
    # Find the table body and append before the final separator line
    awk -v op="${OPERATION_CLEAN}" \
        -v dur="${DURATION}" \
        '{
            print
            if (/^\|[-| ]+\|$/) {
                print "| " op " | " dur "s | " dur "s | stable | >300s |"
            }
        }' "${PERF_LOG}" > "${tmpfile}" && mv "${tmpfile}" "${PERF_LOG}"
fi

exit ${EXIT_CODE}
