#! /bin/sh
#
# local_proxy.sh
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.
#


rm -f "${PROXY_LOG}";

set -x
SERVER_KEY=$(grep "server_key" /mitmproxy-remote/wireguard.conf | sed -E 's/^.*"server_key"\s*:\s*"([^"]+)".*$/\1/')
CLIENT_KEY=$(grep "client_key" /mitmproxy-remote/wireguard.conf | sed -E 's/^.*"client_key"\s*:\s*"([^"]+)".*$/\1/')

PROXY_REMOTE_ADDRESS=$(dig "${PROXY_REMOTE_HOST}" | \
    grep -E '^'"${PROXY_REMOTE_HOST}"'\.\s+[0-9]+\s+IN\s+A\s+[0-9.]+$' | \
    grep -oE '[0-9.]+$')

{
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

# tbd clone and checkout right branch of cbor4dns to /cbor4dns

proxychains4 mitmdump -v -m transparent --ssl-insecure --showhost -s "${PROXY_LOCAL_SCRIPT}" -p "${PROXY_LOCAL_PORT}"
