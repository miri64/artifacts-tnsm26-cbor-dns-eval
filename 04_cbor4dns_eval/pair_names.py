#! /usr/bin/env python3
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import gzip
import multiprocessing
import os.path
import sys
import traceback

import bounded_pool_executor
import dns.rdatatype

import cbor4dns_utils


NAME_COLS = [
    "dns.qry.name",
    "dns.resp.name",
    "dns.afsdb.hostname",
    "dns.cname",
    "dns.dname",
    "dns.mr",
    "dns.ns",
    "dns.nsec.next_domain_name",
    "dns.ptr.domain_name",
    "dns.rrsig.signers_name",
    "dns.rt.intermediate_host",
    "dns.soa.mname",
    "dns.soa.rname",
    "dns.srv.name",
    "dns.svcb.targetname",
    "dns.winsr.name_result_domain",
]
WRITER = None


def pair_names(row):
    global WRITER
    try:
        for i, col1 in enumerate(NAME_COLS):
            if not row[col1]:
                continue
            for col2 in NAME_COLS[i:]:  # start with same column to apply conversion
                if not row[col2]:
                    continue
                if isinstance(row[col2], str):
                    # col1 is changed by this col2 change as well
                    row[col2] = [name.strip(".") for name in row[col2].split("|")]
                if col1 == col2:
                    continue
                for c1, c2 in [(col1, col1), (col1, col2), (col2, col2)]:
                    for j1, name1 in enumerate(row[c1]):
                        for j2, name2 in enumerate(row[c2]):
                            if c1 == c2 and j1 >= j2:
                                # skip duplicate occurrences
                                continue
                            csb, ccsb = cbor4dns_utils.common_suffixes(name1, name2)
                            out_row = {
                                "dataset": row["dataset"],
                                "pcap": row["pcap"],
                                "frame": row["frame.number"],
                                "protocol": row["frame.protocols"].split(":")[-1],
                                "msg": "r"
                                if row["dns.flags.response"] in ["1", "True"]
                                else "q",
                                "Field x": c1,
                                "Field y": c2,
                                "Name x": name1,
                                "Name y": name2,
                                "Same Name": int(name1 == name2),
                                "Common Suffix Bytes": csb,
                                # add leading delimiter
                                "Common Component Suffix Bytes": ccsb,
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
                "Name x",
                "Name y",
                "Same Name",
                "Common Suffix Bytes",
                "Common Component Suffix Bytes",
            ],
        )
        WRITER.writeheader()
        with bounded_pool_executor.BoundedThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        ) as executor:
            for row in reader:
                executor.submit(pair_names, row)


if __name__ == "__main__":
    main()
