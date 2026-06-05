#! /bin/sh
#
# update_certificate.sh
# Copyright (C) 2026 (C) TU Dresden
#
# Distributed under terms of the MIT license.
#

if [ $# -lt 1 ]; then
    echo "usage: $0 [PEM certificate]" >&2
    exit 1
fi

openssl x509 -in "$1" -inform PEM -out /usr/local/share/ca-certificates/mitmproxy.crt
update-ca-certificates
