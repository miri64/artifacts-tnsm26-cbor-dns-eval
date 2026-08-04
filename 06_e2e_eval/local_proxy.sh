#! /bin/sh
#
# local_proxy.sh
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.
#


rm -f "${PROXY_LOG}";

if echo "${PROXY_REMOTE_HOST}" | grep -qoE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    PROXY_REMOTE_ADDRESS="${PROXY_REMOTE_HOST}"
else
    PROXY_REMOTE_ADDRESS=$(host "${PROXY_REMOTE_HOST}" | \
        grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
fi

{
    echo "tcp_read_time_out 15000"
    echo "tcp_connect_time_out 8000"
    echo "[ProxyList]"
    echo "socks5 ${PROXY_REMOTE_ADDRESS} ${PROXY_REMOTE_PORT}"
} > /etc/proxychains4.conf

iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
iptables -t nat -A PREROUTING -i eth0 -p udp --dport 80 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
iptables -t nat -A PREROUTING -i eth0 -p udp --dport 443 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
ip6tables -t nat -A PREROUTING -i eth0 -p udp --dport 80 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";
ip6tables -t nat -A PREROUTING -i eth0 -p udp --dport 443 -j REDIRECT --to-port "${PROXY_LOCAL_PORT}";

# Remove old certificates from previous sessions (mitmproxy does not seem to reuse them)
rm -f ~/.mitmproxy/mitmproxy-*

proxychains4 mitmdump -m transparent --ssl-insecure --anticache -s "${PROXY_LOCAL_SCRIPT}" -p "${PROXY_LOCAL_PORT}" --set connection_strategy=lazy > /dev/null
