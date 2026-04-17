#! /bin/sh
#
# init_chrome.sh
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.
#

apt-get update && apt-get install -y iproute2 dnsutils openssl

env

while curl -m 1 -s http://mitm.it | grep -q "If you can see this, traffic is not going through mitmproxy."; do
    LOCAL_PROXY_ADDRESS=$(dig local-proxy | grep -E '^local-proxy\.\s+[0-9]+\s+IN\s+A\s+[0-9.]+$' | grep -oE '[0-9.]+$')

    if [ -n "${LOCAL_PROXY_ADDRESS}" ]; then
        if ! ip route | grep -q "default.*${LOCAL_PROXY_ADDRESS}"; then
            ip route delete default
        fi
        ip route add default via "${LOCAL_PROXY_ADDRESS}"
    else
        echo "Unable to get local-proxy address for gateway" >&2
        exit 1
    fi
done

if [ "${SLEEP_AFTER_INIT:-1}" -eq "1" ]; then
    while true; do
        sleep 3600;
    done
fi
