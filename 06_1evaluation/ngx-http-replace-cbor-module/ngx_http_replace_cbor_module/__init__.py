#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Martine S. Lenders <martine.lenders@tu-dresden.de>
#
# Distributed under terms of the MIT license.

import cbor2


def json2cbor(json_str):
    return f"{cbor2} loaded {json_str}".encode()
