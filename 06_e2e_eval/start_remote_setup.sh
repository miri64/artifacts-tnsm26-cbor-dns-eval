#!/bin/sh

CMD=up

if [ $# -gt 0 ]; then
    CMD="$1"
    shift 1
fi


PROXY_REMOTE_LOG=output-dataset/mitmproxy-$(date +%s)-remote.log docker compose -f docker-compose-remote.yaml "${CMD}" $*
