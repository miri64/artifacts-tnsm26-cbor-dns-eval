#! /bin/bash
#
# web_client.sh
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROCS=$(grep -c '^processor' /proc/cpuinfo)
if [ $PROCS -gt 8 ]; then
    # leave some resources to collegues ;-)
    PROCS=8   #$(( (PROCS * 3) / 4))
fi
COUNT=1000
DATABASE="${SCRIPT_DIR}/output_datasets/http-archive.db"
DOH_PORT=8053
HTTP_PORT=8888
HTTPS_PORT=8433
COMPRESSED_FLAG=

while getopts "d:gn:p:s:D:" opt; do
    case "${opt}" in
        d)  DATABASE="${OPTARG}";;
        D)  DOH_PORT="${OPTARG}";;
        g)  COMPRESSED_FLAG="--compressed";;
        n)  COUNT="${OPTARG}";;
        p)  HTTP_PORT="${OPTARG}";;
        s)  HTTPS_PORT="${OPTARG}";;
        *)  ;;
    esac
done

if [ "$COUNT" -le 1 ]; then
    COUNT=1
fi

HEADER="%{url_effective}\t%{content_type}\t%{http_version}\t%{time_namelookup}\t"
HEADER="${HEADER}%{time_connect}\t%{time_appconnect}\t%{time_pretransfer}\t%{time_redirect}\t"
HEADER="${HEADER}%{time_starttransfer}\t%{time_total}\n"

echo -ne "after_time\tstart_time\tdoh_a_completed\tdoh_aaaa_completed\treq_time\tbefore_time\tid\turl\ttype\t${HEADER}" | sed -e 's/%{//g' -e 's/}//g'

request() {
    ID=$(echo "$1" | cut -f1 -d\|)
    URL=$(echo "$1" | cut -f2 -d\|)
    TYPE=$(echo "$1" | cut -f3 -d\|)

    if [[ ${URL} == http:* ]]; then
        PORT="${HTTP_PORT}"
        SPORT=80
    elif [[ ${URL} == https:* ]]; then
        PORT="${HTTPS_PORT}"
        SPORT=443
    fi
    if [[ ${URL} == *"?"* ]]; then
        if [[ ${URL} == *"?" ]]; then
            SEP=""
        else
            SEP="&"
        fi
    else
        SEP="?"
    fi
    HOST_PART=$(echo "${URL}" | sed -E 's#^https?://([^/]+)/.*$#\1#')
    if ! [[ ${HOST_PART} == *":"* ]]; then
        HOST_PART="${HOST_PART}:${SPORT}"
    fi
    HOST=$(echo "${HOST_PART}" | cut -d: -f1)
    URL=$(echo "${URL}" | sed -e 's/\[/\\[/g' -e 's/]/\\]/g' -e 's/{/\\{/g' -e 's/}/\\}/g')
    TRACE_FILE=$(mktemp)
    trap "rm -f '${TRACE_FILE}'" SIGINT SIGQUIT SIGTERM SIGKILL
    for i in $(seq "${COUNT}"); do
        ERR_FILE=$(mktemp)
        trap "rm -f '${ERR_FILE}'" SIGINT SIGQUIT SIGTERM SIGKILL
        BEFORE_CURL=$(echo "" | ts "%.s" | xargs echo)
        curl -k -f -s -S --fail-early --trace - --no-sessionid \
             --cacert "${SCRIPT_DIR}/domain.crt" \
             --doh-url "https://localhost:${DOH_PORT}/delegate" \
             --connect-to "${HOST_PART}:${HOST}:${PORT}" \
             ${COMPRESSED_FLAG} \
             -H 'Accept-Encoding: gzip' \
             -H 'Connection: close' \
             -H 'Cache-Control: no-cache, no-store' \
             -H 'Pragma: no-cache'  \
             -w "CSV\t${BEFORE_CURL}\t${ID}\t${URL}\t${TYPE}\t${HEADER}" \
            "${URL}${SEP}exp_count=${i}" 2> "${ERR_FILE}" \
            | ts '%.s' >> "${TRACE_FILE}"
        CURL_STATUS=$?
        AFTER_CURL=$(echo "" | ts "%.s" | xargs echo)
        if [ "${CURL_STATUS}" -eq 22 ]; then   # HTTP error occurred, don't count this page
            echo "HTTP error occurred on ${URL} (id=${ID})" >&2
            cat "${ERR_FILE}" | grep "^curl:" >&2
            rm -f "${ERR_FILE}"
            exit 0
        elif [ "${CURL_STATUS}" -eq 6 ]; then   # Hostname was not resolvable
            echo "Hostname not resolvable on ${URL} (id=${ID})" >&2
            cat "${ERR_FILE}" | grep "^curl:" >&2
            rm -f "${ERR_FILE}"
            exit 0
        elif [ "${CURL_STATUS}" -ne 0 ]; then  # cURL had another error, stop for user to check
            cat "${ERR_FILE}" >&2
            rm -f "${TRACE_FILE}"
            rm -f "${ERR_FILE}"
            exit 1
        fi
        rm -f "${ERR_FILE}"
    done || exit 1
    cat "${TRACE_FILE}" | \
        awk -F'\t' '
            $0 ~ /Info: Connecting to port:/ { \
                printf "%s\t", gensub(/^([0-9]+\.[0-9]+).*/, "\\1", "g", $0); \
            } \
            $0 ~ /a DOH request is completed, 1 to go/ {
                printf "%s\t", gensub(/^([0-9]+\.[0-9]+).*/, "\\1", "g", $0); \
            }
            $0 ~ /a DOH request is completed, 0 to go/ {
                printf "%s\t", gensub(/^([0-9]+\.[0-9]+).*/, "\\1", "g", $0); \
            }
            $0 ~ /Send header/ { \
                printf "%s\t", gensub(/^([0-9]+\.[0-9]+).*/, "\\1", "g", $0); \
            } \
            $0 ~ /^[0-9]+\.[0-9]+ CSV/ { \
                print gensub(/^[0-9]+\.[0-9]+ CSV\t/, "", "g", $0); \
            }' | awk -v after_time="${AFTER_CURL}" -F'\t' ' \
            NF == 15 { \
                printf "%s\t\t\t\t\t%s\n", after_time, $0; \
            } \
            NF == 16 { \
                printf "%s\t%s\t%s\t\t\t", after_time, $1, $2; \
                for (i = 3; i <= NF; i++) printf "%s%s", $(i), (i < NF) ? "\t" : "\n"; \
            } \
            NF == 17 { \
                printf "%s\t%s\t%s\t%s\t\t", after_time, $1, $2, $3; \
                for (i = 4; i <= NF; i++) printf "%s%s", $(i), (i < NF) ? "\t" : "\n"; \
            } \
            NF == 18 { printf "%s\t%s\n", after_time, $0 }'
    rm -f "${TRACE_FILE}"
}

export -f request
export SCRIPT_DIR
export COUNT
export DOH_PORT
export HTTP_PORT
export HTTPS_PORT
export HEADER
export COMPRESSED_FLAG

PROCS=1
sqlite3 "${DATABASE}" "SELECT id, url, type FROM objects" | \
    parallel --line-buffer -j${PROCS} --halt-on-error soon,fail=1 request
