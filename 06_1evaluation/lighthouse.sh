#! /bin/bash
#
# lighthouse.sh
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

TRANCO_LIST="${TRANCO_LIST:-"${SCRIPT_DIR}"/tranco_3QL4L.csv}"
LIGHTHOUSE_RUNS="${LIGHTHOUSE_RUNS:-3}"
MARKER_DOMAIN="${MARKER_DOMAIN:-tud.de}"
TRANCO_LIST_LEN=$(wc -l "${TRANCO_LIST}" | awk '{print $1}')
TRANCO_LOWER_LIMIT="${TRANCO_LOWER_LIMIT:-0}"
TRANCO_UPPER_LIMIT="${TRANCO_UPPER_LIMIT:-50}"

export SLEEP_AFTER_INIT=0
/init.sh

tranco_subset() {
    awk \
        -v tlength="${TRANCO_LIST_LEN}"\
        -v lower="${TRANCO_LOWER_LIMIT}"\
        -v upper="${TRANCO_UPPER_LIMIT}"\
        -F, \
        '(FNR > lower && FNR <= upper) || (FNR > (tlength - upper) && FNR <= (tlength - lower)) {gsub("\r","",$2); print $1,$2}' \
        "${TRANCO_LIST}"
}

if tranco_subset | grep -qF "${MARKER_DOMAIN}"; then
    echo "Marker domain ${MARKER_DOMAIN} in tested tranco subset" >&2
fi

rm -f /config/tls_configured

sleep 5

/app/update_certificate.sh /mitmproxy-local/mitmproxy-ca-cert.pem

COUNT=0

while ! [ -f /config/tls_configured ]; do
    [ "$(( COUNT % 6 ))" -eq "0" ] && {
        echo -e "\033[1;31mPlease configure the local proxy and Chrome with the mitmproxy "
        echo -e "\033[1;31mcertificates. For the local proxy use docker \`exec\` with bash "
        echo -e "\033[1;31mand configure them for a Debian system. For Chrome go to "
        echo -e "\033[1;31mhttps://localhost:3001. See "
        echo -e "\033[1;31mhttps://docs.mitmproxy.org/archive/v12/concepts/certificates/ "
        echo -e "\033[1;31mfor how to do that. Set the DNS provider of Chrome to "
        echo -e "\033[1;31mhttps://dns.google/dns-query and use docker \`exec\` to "
        echo -e "\033[1;31m\`touch ~/tls_configured\`. The experiments will start "
        echo -e "\033[1;31mshortly after. You can then close the https://localhost:3001 tab.\033[0m"
        echo -e "\033[1;31m\033[0m"
        echo -e "\033[1;31mDO NOT CLOSE CHROME WITHIN THAT TAB!\033[0m"
        echo ""
    } >&2
    sleep 5
    COUNT=$(( COUNT + 1 ))
done

export PATH="${PATH}:/bin/versions/node/v24.14.1/bin/"
USER="$(id -nu "${PUID}")"

mkdir -p /app/output-dataset

for run in $(seq 2 "${LIGHTHOUSE_RUNS}"); do
    for convert in "true" "false"; do
        tranco_subset | while read nr domain; do
            for packed in "false"; do
                if [ "${convert}" = "false" ] && [ "${packed}" = "true" ]; then
                    continue
                fi
                LIGHTHOUSE_TS=$(date "+%s")
                curl -s -m 1 -X POST -k https://"${MARKER_DOMAIN}" -d "{\"marker\":true,\"domain\":\"${domain}\",\"rank\":${nr},\"run\":${run},\"signal\":\"start\",\"convert\":${convert},\"packed\":${packed},\"lhts\":${LIGHTHOUSE_TS}}"
                chown -R "${USER}:" /app/output-dataset
                LIGHTHOUSE_OUTPUT_PATH="/app/output-dataset/lighthouse-run-${domain}-$(printf "%03d" "${run}")-${convert}-${packed}-${LIGHTHOUSE_TS}${LIGHTHOUSE_LOG_EXTRA}"
                su - "${USER}" -c "export PATH='${PATH}'; lighthouse 'https://${domain}' -GA '${LIGHTHOUSE_OUTPUT_PATH}-artifacts' --output-path='${LIGHTHOUSE_OUTPUT_PATH}' --output=json --output=html --output=csv --port 9159"
                curl -s -m 1 -X POST -k https://"${MARKER_DOMAIN}" -d "{\"marker\":true,\"domain\":\"${domain}\",\"rank\":${nr},\"run\":${run},\"signal\":\"end\",\"convert\":${convert},\"packed\":${packed},\"lhts\":${LIGHTHOUSE_TS}}"
            done
        done
    done
done
