#!/usr/bin/env bash
#
# Copyright (C) 2024-26 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

export INPUT_PATH="${INPUT_PATH:-${SCRIPT_DIR}/input_datasets}"
HARCH_JSONS="${SCRIPT_DIR}/harch_jsons.csv"

cat "${INPUT_PATH}"/bq-results-*.csv | \
    awk -F, 'BEGIN { \
      FPAT = "([^,]+)|(\"[^\"]+\")"; \
      OFS="\t" \
    } {print $1, $2}' | \
    while IFS=$'\t' read url user_agent; do
        [ -f "${HARCH_JSONS}" ] && grep -q -F "${url}" "${HARCH_JSONS}" || \
        curl -s -A "${user_agent}" "${url}" | "${SCRIPT_DIR}"/harch_dl.py "${url}" \
        >> "${HARCH_JSONS}"
    done
