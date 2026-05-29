#!/usr/bin/env bash
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
OUTPUT_DATASETS=${OUTPUT_DATASETS:-"${SCRIPT_DIR}/output_datasets"}

echo "dataset,pcap,frame,protocol,msg,qtype,w_query,packed,tier,content type,redundancy,structure" | \
    pigz > "${OUTPUT_DATASETS}"/dns_cbor_classic_taxonomy.csv.gz

zcat "${OUTPUT_DATASETS}"/dns_cbor_classic_encoding_{iot,tranco}.csv.gz | \
    awk -F, 'OFS="," {print $1,$2,$3,$4,$5,$6,$7,$10,$11,$12,$13}' | \
    parallel -j128 --pipe --line-buffer "${SCRIPT_DIR}"/cbor-dns-taxonomy.py | \
    pigz >> "${OUTPUT_DATASETS}"/dns_cbor_classic_taxonomy.csv.gz
