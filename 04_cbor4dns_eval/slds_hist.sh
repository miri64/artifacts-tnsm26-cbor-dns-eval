#!/bin/bash
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROCS=${PROCS:-$(grep -c '^processor' /proc/cpuinfo)}
OUTPUT_DATASETS="${OUTPUT_DATASETS:-"${SCRIPT_DIR}/output_datasets"}"

zcat "${OUTPUT_DATASETS}"/dns_names_tranco.csv.gz "${OUTPUT_DATASETS}"/dns_names_iot.csv.gz | \
    "${SCRIPT_DIR}"/slds_hist.py | pigz > "${OUTPUT_DATASETS}"/dns_names_slds_hist_tranco_iot.csv.gz
(
    zcat "${OUTPUT_DATASETS}"/dns_names_slds_hist_tranco_iot.csv.gz | \
        "${SCRIPT_DIR}"/categorize_slds.py --header
    zcat "${OUTPUT_DATASETS}"/dns_names_slds_hist_tranco_iot.csv.gz | \
        parallel -j${PROCS} --pipe --line-buffer "${SCRIPT_DIR}"/categorize_slds.py
) | \
        pigz > "${OUTPUT_DATASETS}"/dns_names_slds_hist_categories_tranco_iot.csv.gz

zcat "${OUTPUT_DATASETS}"/dns_names_secspider.csv.gz "${OUTPUT_DATASETS}"/dns_names_tls.csv.gz | \
    "${SCRIPT_DIR}"/slds_hist.py | pigz > "${OUTPUT_DATASETS}"/dns_names_slds_hist_secspider_tls.csv.gz
(
    zcat "${OUTPUT_DATASETS}"/dns_names_slds_hist_secspider_tls.csv.gz | \
        "${SCRIPT_DIR}"/categorize_slds.py --header
    zcat "${OUTPUT_DATASETS}"/dns_names_slds_hist_secspider_tls.csv.gz | \
        parallel -j${PROCS} --pipe --line-buffer "${SCRIPT_DIR}"/categorize_slds.py
) | \
        pigz > "${OUTPUT_DATASETS}"/dns_names_slds_hist_categories_secspider_tls.csv.gz
