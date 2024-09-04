#! /usr/bin/env python3
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import gzip
import io
import multiprocessing
import pathlib
import subprocess
import sys
import traceback

import dns.rdatatype

import cbor4dns_utils

SCRIPT_PATH = pathlib.Path(__file__).resolve().parent
CBOR4DNS_PATH = (SCRIPT_PATH / "cbor4dns").resolve()
TAG_TYPE = ""
PACKED_VAL = 1
WRITER = None


if CBOR4DNS_PATH not in sys.path:
    sys.path.append(str(CBOR4DNS_PATH))
import cbor4dns.encode


def encode(row):
    global PACKED_VAL, TAG_TYPE, WRITER
    try:
        with io.BytesIO() as cbor_file:
            with io.BytesIO() as cbor_packed_file:
                cbor_encoder = cbor4dns.encode.Encoder(
                    cbor_file, packed=False, always_omit_question=False
                )
                cbor_packed_encoder = cbor4dns.encode.Encoder(
                    cbor_packed_file, packed=True, always_omit_question=False
                )
                if row.get("dns.query_payload"):
                    with io.BytesIO() as cbor_query_file:
                        cbor_query_encoder = cbor4dns.encode.Encoder(
                            cbor_query_file, packed=False, always_omit_question=False
                        )
                        cbor_query_encoder.encode(
                            bytes.fromhex(row["dns.query_payload"])
                        )
                        orig_query = cbor_query_file.getvalue()
                else:
                    orig_query = None

                payload = bytes.fromhex(row["payload"])

                if PACKED_VAL != "lite":
                    cbor_encoder.encode(payload, orig_query)
                    cbor = cbor_file.getvalue()
                else:
                    cbor = None

                if row["dns.flags.response"] in ["True", "1"]:
                    cbor_packed_encoder.encode(payload, orig_query)
                    cbor_packed = cbor_packed_file.getvalue()
                else:
                    cbor_packed = b""
        out_row = {
            "dataset": row["dataset"],
            "pcap": row["pcap"],
            "frame": row["frame.number"],
            "protocol": row["frame.protocols"].split(":")[-1],
            "msg": "r" if row["dns.flags.response"] in ["1", "True"] else "q",
            "w_query": bool(row.get("dns.query_payload", "")),
            "application/dns-message data": row["payload"],
            "application/dns-message len": len(payload),
        }
        if cbor is not None:
            out_row[f"application/cbor+dns{TAG_TYPE} data"] = cbor.hex()
            out_row[f"application/cbor+dns{TAG_TYPE} len"] = len(cbor)
        if row["dns.flags.response"] in ["True", "1"]:
            out_row[
                f"application/cbor+dns;packed={PACKED_VAL}{TAG_TYPE} data"
            ] = cbor_packed.hex()
            out_row[f"application/cbor+dns;packed={PACKED_VAL}{TAG_TYPE} len"] = len(
                cbor_packed
            )
        for query_type in row["dns.qry.type"].split("|"):
            type_name = dns.rdatatype.RdataType(int(query_type)).name
            out_row["qtype"] = type_name
            WRITER.writerow(out_row)
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print("Error:", e, "on", row, file=sys.stderr)
        print("=========================================", file=sys.stderr)
        print("payload:", row["payload"], file=sys.stderr)
        print("query payload:", row["dns.query_payload"], file=sys.stderr)
        sys.stderr.flush()


def main():
    global PACKED_VAL, TAG_TYPE, WRITER
    parser = argparse.ArgumentParser()
    if hasattr(cbor4dns.encode, "RefIdx"):
        parser.add_argument(
            "-t",
            "--tag",
            type=int,
            default=7,
            help="Tag number for name compression referencing",
        )
    parser.add_argument("--header", action="store_true")
    parser.add_argument(metavar="<Input CSV filename>", dest="csv")
    args = parser.parse_args()

    # use maximum possible size for field size
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = (max_int >> 2)

    git_branch = subprocess.check_output(
        ["git", "-C", str(CBOR4DNS_PATH), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
    ).strip()
    if git_branch == "packed-lite":
        PACKED_VAL = "lite"
    if hasattr(cbor4dns.encode, "RefIdx"):
        cbor4dns.encode.RefIdx.tag = args.tag
        TAG_TYPE = f" t{args.tag}"
        PACKED_VAL = "str-ref"
    if args.csv.endswith(".gz"):
        open_func = gzip.open
    else:
        open_func = open
    with open_func(args.csv, "rt", encoding="utf-8") as in_csvfile:
        reader = csv.DictReader(in_csvfile, delimiter=";")
        fieldnames=reader.fieldnames
        del reader
    in_csvfile = sys.stdin
    reader = csv.DictReader(in_csvfile, delimiter=";", fieldnames=fieldnames)
    out_csvfile = sys.stdout
    fieldnames = [
        "dataset",
        "pcap",
        "frame",
        "protocol",
        "msg",
        "qtype",
        "w_query",
        "application/dns-message data",
        "application/dns-message len",
    ]
    if PACKED_VAL != "lite":
        fieldnames.extend(
            [
                f"application/cbor+dns{TAG_TYPE} data",
                f"application/cbor+dns{TAG_TYPE} len",
            ]
        )
    fieldnames.extend(
        [
            f"application/cbor+dns;packed={PACKED_VAL}{TAG_TYPE} data",
            f"application/cbor+dns;packed={PACKED_VAL}{TAG_TYPE} len",
        ]
    )
    manager = multiprocessing.Manager()
    WRITER = cbor4dns_utils.FlushableThreadSafeDictWriter(
        out_csvfile,
        manager,
        delimiter=",",
        fieldnames=fieldnames,
    )
    if args.header:
        WRITER.writeheader()
        return
    for row in reader:
        if row["dataset"] == "dataset":
            continue
        encode(row)


if __name__ == "__main__":
    main()
