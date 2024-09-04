#! /usr/bin/env python3
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import gzip
import ipaddress
import multiprocessing
import os.path
import sys
import traceback

import bounded_pool_executor
import dns.rdatatype

import cbor4dns_utils


ADDR_COLS = [
    "_ws.col.Source",
    "_ws.col.Destination",
    "dns.a",
    "dns.aaaa",
    "dns.apl.afdpart.ipv4",
    "dns.apl.afdpart.ipv6",
    "dns.ilnp.l32",
    "dns.ipseckey.gateway_ipv4",
    "dns.ipseckey.gateway_ipv6",
    "dns.svcb.svcparam.ipv4hint.ip",
    "dns.svcb.svcparam.ipv6hint.ip",
    "dns.wins.wins_server",
    "dns.wks.address",
    "dns.xpf.destination_ipv4",
    "dns.xpf.destination_ipv6",
    "dns.xpf.source_ipv4",
    "dns.xpf.source_ipv6",
]


WRITER = None


def pair_addrs(row):
    try:
        for i, col1 in enumerate(ADDR_COLS):
            if not row[col1]:
                continue
            for col2 in ADDR_COLS[i:]:
                if not row[col2]:
                    continue
                if isinstance(row[col2], str):
                    # col1 is changed by this col2 change as well
                    row[col2] = [
                        ipaddress.ip_address(addr).packed
                        for addr in row[col2].split("|")
                    ]
                if col1 == col2 or (
                    col1 == "_ws.col.Source" and col2 == "_ws.col.Destination"
                ):
                    continue
                for c1, c2 in [(col1, col1), (col1, col2), (col2, col2)]:
                    if c1.startswith("dns.") and c2.startswith("dns."):
                        prot = row["frame.protocols"].split(":")[-1]
                    else:
                        prot = "xlayer"
                    for j1, addr1 in enumerate(row[c1]):
                        for j2, addr2 in enumerate(row[c2]):
                            if len(addr1) != len(addr2):
                                continue
                            if c1 == c2 and j1 >= j2:
                                # skip duplicate occurrences
                                continue
                            out_row = {
                                "dataset": row["dataset"],
                                "pcap": row["pcap"],
                                "frame": row["frame.number"],
                                "protocol": prot,
                                "msg": "r"
                                if row["dns.flags.response"] in ["1", "True"]
                                else "q",
                                "Field x": c1,
                                "Field y": c2,
                                "Address x": addr1.hex(),
                                "Address y": addr2.hex(),
                                "Common Prefix Bytes": len(
                                    os.path.commonprefix([addr1, addr2])
                                ),
                            }
                            for query_type in row["dns.qry.type"].split("|"):
                                type_name = dns.rdatatype.RdataType(
                                    int(query_type)
                                ).name
                                out_row["qtype"] = type_name
                                WRITER.writerow(out_row)
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print("Error:", e, "on", row, file=sys.stderr)


def main():
    global WRITER
    parser = argparse.ArgumentParser()
    parser.add_argument(metavar="<Input CSV filename>", dest="csv")
    args = parser.parse_args()
    if args.csv.endswith(".gz"):
        open_func = gzip.open
    else:
        open_func = open

    # use maximum possible size for field size
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = (max_int >> 2)

    with open_func(args.csv, "rt", encoding="utf-8") as in_csvfile:
        reader = csv.DictReader(in_csvfile, delimiter=";")
        out_csvfile = sys.stdout
        manager = multiprocessing.Manager()
        WRITER = cbor4dns_utils.FlushableThreadSafeDictWriter(
            out_csvfile,
            manager,
            delimiter=",",
            fieldnames=[
                "dataset",
                "pcap",
                "frame",
                "protocol",
                "msg",
                "qtype",
                "Field x",
                "Field y",
                "Address x",
                "Address y",
                "Common Prefix Bytes",
            ],
        )
        WRITER.writeheader()
        with bounded_pool_executor.BoundedThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        ) as executor:
            for row in reader:
                executor.submit(pair_addrs, row)


if __name__ == "__main__":
    main()
