#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import csv
import sys

import publicsuffixlist


HIST = {}
FIELDNAMES = ["dataset", "protocol", "msg", "qtype", "level", "suffix", "count"]


if __name__ == "__main__":
    reader = csv.DictReader(sys.stdin, delimiter=",")
    writer = csv.DictWriter(
        sys.stdout,
        delimiter=",",
        fieldnames=FIELDNAMES
    )
    psl = publicsuffixlist.PublicSuffixList()
    for row in reader:
        try:
            ccsb = int(row["Common Component Suffix Bytes"])
            same_name = bool(int(row["Same Name"]))
        except ValueError:
            # hit a header in the cat'ed files
            continue
        if ccsb == 1:
            suffix = ""
        elif same_name:
            suffix = row["Name y"]
        else:
            suffix = row["Name y"][-(ccsb - 1):]
        sld = psl.privatesuffix(suffix.lower())
        if sld is not None:
            level = "sld"
        else:
            sld = suffix.lower()
            level = "tld" if suffix else ""
        key = (
            row["dataset"],
            row["protocol"],
            row["msg"],
            row["qtype"],
            level,
            sld,
        )
        if key in HIST:
            HIST[key] += 1
        else:
            HIST[key] = 1
    writer.writeheader()
    for key, value in HIST.items():
        writer.writerow(dict(zip(FIELDNAMES, list(key) + [value])))
