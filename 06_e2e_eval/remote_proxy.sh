#! /bin/sh
#
# remote_proxy.sh
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.
#



rm -f "${PROXY_LOG}"; \
rm -f ~/.mitmproxy/mitmproxy-*; \

mitmdump -m socks5 -s "${PROXY_SCRIPT}" -p "${PROXY_PORT}" --set connection_strategy=lazy --set block_global=false > /dev/null
