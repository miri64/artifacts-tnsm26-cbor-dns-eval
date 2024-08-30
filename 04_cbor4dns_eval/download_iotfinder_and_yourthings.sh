#!/usr/bin/env bash
#
# collect_dns_hex.sh
# Copyright (C) 2023 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
INPUT_DATASETS="${SCRIPT_DIR}/input_datasets"

IOTFINDER_URLS=(
    "https://www.dropbox.com/s/3tv44ywzyahy3km/dns_2019_08.tgz?dl=0"
    "https://www.dropbox.com/s/v5pga0qpnywe1et/dns_2019_09.tgz?dl=0"
)
YOURTHINGS_URLS=(
    "https://www.dropbox.com/s/0jltu5o4a9kk7z8/iot_traffic20180320.tgz?dl=0"
    "https://www.dropbox.com/s/xo75oan8juoyb9o/iot_traffic20180321.tgz?dl=0"
    "https://www.dropbox.com/s/2iolbgnaw68cpb0/iot_traffic20180328.tgz?dl=0"
    "https://www.dropbox.com/s/blyem2vfbwbwd4h/iot_traffic20180410.tgz?dl=0"
    "https://www.dropbox.com/s/rcodps77sot88xl/iot_traffic20180411.tgz?dl=0"
    "https://www.dropbox.com/s/ldpkjs799wxf7la/iot_traffic20180412.tgz?dl=0"
    "https://www.dropbox.com/s/z11dgm9u6kuzvml/iot_traffic20180413.tgz?dl=0"
    "https://www.dropbox.com/s/2j62g8qxhby4sqh/iot_traffic20180414.tgz?dl=0"
    "https://www.dropbox.com/s/n6epxutlemcrcrp/iot_traffic20180415.tgz?dl=0"
    "https://www.dropbox.com/s/tfrhq7noobgxpi0/iot_traffic20180416.tgz?dl=0"
    "https://www.dropbox.com/s/gsly960mzi6f0on/iot_traffic20180417.tgz?dl=0"
    "https://www.dropbox.com/s/8klt5f9fr164f5n/iot_traffic20180418.tgz?dl=0"
    "https://www.dropbox.com/s/c0uxli3cirzill1/iot_traffic20180419.tgz?dl=0"
)

download_dataset() {
    name="${1}"
    urls=(${@})
    unset urls[0]

    mkdir -p "${INPUT_DATASETS}/${name}"
    for url in ${urls[@]}; do
        curl -L "$url" | tar -xz -C "${INPUT_DATASETS}/${name}"
    done
}

download_dataset "iotfinder" "${IOTFINDER_URLS[@]}"
download_dataset "yourthings" "${YOURTHINGS_URLS[@]}"
