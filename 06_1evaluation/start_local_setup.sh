#!/bin/sh

CMD=up

if [ $# -gt 0 ]; then
    CMD="$1"
    shift 1
fi

if ! [ -d chrome-config ]; then
    mkdir -p chrome-config/.config/google-chrome-lighthouse/
fi

PUID=$(id -u) PGID=$(id -g) PROXY_REMOTE_HOST="${PROXY_REMOTE_HOST:-remote-proxy}" PROXY_REMOTE_PORT="${PROXY_REMOTE_PORT:-8081}" PROXY_LOCAL_LOG=output-dataset/mitmproxy-$(date +%s)-local.log docker compose -f docker-compose-local.yaml -f docker-compose-lighthouse.yaml "${CMD}" $*
