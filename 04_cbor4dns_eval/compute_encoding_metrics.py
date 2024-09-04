#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import gzip
import multiprocessing
import sys

import cbor4dns_utils


WRITER = None


def cr(base_len, compare_len):
    return base_len / compare_len


def gain(base_len, compare_len):
    return 1 - (compare_len / base_len)


def byte_savings(base_len, compare_len):
    return base_len - compare_len


def calculate(row, base_format, compare_formats):
    global WRITER
    try:
        out_row = {
            "dataset": row["dataset"],
            "pcap": row["pcap"],
            "frame": int(row["frame"]),
            "protocol": row["protocol"],
            "msg": row["msg"],
            "qtype": row["qtype"],
            "w_query": row["w_query"]
        }
        has_metrics = False
        for form in compare_formats:
            if row[f"{form} len"] and row[f"{base_format} len"]:
                has_metrics = True
                out_row[f"{base_format} vs {form} cr"] = cr(
                    int(row[f"{base_format} len"]),
                    int(row[f"{form} len"]),
                )
                out_row[f"{base_format} vs {form} gain"] = gain(
                    int(row[f"{base_format} len"]),
                    int(row[f"{form} len"]),
                )
                out_row[f"{base_format} vs {form} byte savings"] = byte_savings(
                    int(row[f"{base_format} len"]),
                    int(row[f"{form} len"]),
                )
        if has_metrics:
            WRITER.writerow(out_row)
    except Exception as e:
        print("Error:", e, "on", row, file=sys.stderr)


def main():
    global WRITER
    parser = argparse.ArgumentParser()
    parser.add_argument(
        metavar="<Base format>",
        dest="base",
        help="Fotmat to compare against"
    )
    parser.add_argument("--header", action="store_true")
    parser.add_argument("--exclude-format-file")
    parser.add_argument(
        metavar="<Encoding CSV file>",
        dest="csv",
        help="CSV file that contains at least one encoding for DNS messages.",
    )
    args = parser.parse_args()

    # use maximum possible size for field size
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = (max_int >> 2)

    if args.csv.endswith(".gz"):
        open_func = gzip.open
    else:
        open_func = open
    with open_func(args.csv, "rt", encoding="utf-8") as in_csvfile:
        reader = csv.DictReader(in_csvfile)
        fieldnames = reader.fieldnames
    in_csvfile = sys.stdin
    reader = csv.DictReader(in_csvfile, fieldnames=fieldnames)
    exclude = None
    if args.exclude_format_file:
        with open(args.exclude_format_file) as exclude_format_file:
            exclude = [l.strip() for l in exclude_format_file.readlines()]
    formats = [
        f.replace(" len", "")
        for f in reader.fieldnames
        if f.endswith(" len") and f not in [
            f"{e} len" for e in (exclude or [])
        ]
    ]
    if args.base not in formats:
        raise ValueError(
            f"Base format \"{args.base}\" not found in CSV header or excluded"
        )
    compare_formats = [f for f in formats if f != args.base]
    cols = [
        f"{args.base} vs {f} {metric}"
        for f in compare_formats
        for metric in ["cr", "gain", "byte savings"]
    ]
    manager = multiprocessing.Manager()
    print(f"Comparing {args.base} vs", file=sys.stderr)
    for form in compare_formats:
        print(f"- {form}", file=sys.stderr)
    out_csvfile = sys.stdout
    WRITER = cbor4dns_utils.FlushableThreadSafeDictWriter(
        out_csvfile,
        manager,
        delimiter=",",
        fieldnames=[
            "dataset", "pcap", "frame", "protocol", "msg", "qtype", "w_query"
        ] + cols,
    )
    if args.header:
        WRITER.writeheader()
        return
    for row in reader:
        if row["frame"] == "frame":
            continue
        calculate(row, args.base, compare_formats)


if __name__ == "__main__":
    main()
