#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Martine S. Lenders <martine.lenders@tu-dresden.de>
#
# Distributed under terms of the MIT license.

import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import cbor2

sys.path.append(
    str((pathlib.Path(__file__).parent.resolve() / ".." / "utils").resolve())
)
from taxonomy import main as taxonomy


if __name__ == "__main__":
    for line in sys.stdin:
        cbor_hexs = line.strip().split(",")
        if len(cbor_hexs) < 4 or not re.match("^[0-9a-fA-F]+$", cbor_hexs[7]):
            print(f"\"{line.strip()}\" not hex", file=sys.stderr)
            continue
        assert len(cbor_hexs[7:]) <= 4
        for packed, (cbor_hex, cbor_len) in enumerate(
            zip(cbor_hexs[7::2], cbor_hexs[8::2])
        ):
            if not cbor_hex or not cbor_len:
                continue
            cbor_len = int(cbor_len.strip())
            tax = taxonomy(cbor2.loads(bytes.fromhex(cbor_hex)))
            if cbor_len < 100:
                tax[0] = 1
            elif cbor_len < 1000:
                tax[0] = 2
            else:
                tax[0] = 3
            print(
                cbor_hexs[0],       # dataset
                cbor_hexs[1],       # pcap
                cbor_hexs[2],       # frame
                cbor_hexs[3],       # protocol
                cbor_hexs[4],       # msg
                cbor_hexs[5],       # qtype
                cbor_hexs[6],       # w_query
                bool(packed),       # packed
                tax[0],             # tier
                tax[1].strip(),     # content type
                tax[2].strip(),     # redundancy
                tax[3].strip(),     # structure
                file=sys.stdout,
                sep=",",
            )
            sys.stdout.flush()
