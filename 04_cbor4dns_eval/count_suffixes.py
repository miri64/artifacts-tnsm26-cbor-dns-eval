#! /usr/bin/env python3
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import gzip
import sys


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(metavar="<Input CSV filename>", dest="csv")
    args = parser.parse_args()
    if args.csv == "-":
        open_func = lambda *args, **kwargs: sys.stdin
    elif args.csv.endswith(".gz"):
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
        for row in reader:
            suffixes = dict()
            for col in NAME_COLS:
                if row[col]:
                    names = row[col].split("|")
                    for name in names:
                        components = name.split(".")
                        for i in range(len(components)):
                            suffix = tuple(components[i:])
                            if suffix in suffixes:
                                suffixes[suffix] += 1
                            else:
                                suffixes[suffix] = 1
            print(len(suffixes))


if __name__ == "__main__":
    main()
