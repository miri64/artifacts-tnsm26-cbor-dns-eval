#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import concurrent.futures
import csv
import os
import pathlib
import sys
import traceback

from dns.rdatatype import (
    CNAME,
    DNAME,
    NS,
    NSEC,
    SOA,
    RdataType,
)

from cbor4dns_utils import decode_name, common_suffixes


SCRIPT_PATH = pathlib.Path(__file__).resolve().parent
INPUT_DATASETS = pathlib.Path(
    os.environ.get("INPUT_DATASETS", SCRIPT_PATH / "input_datasets")
)
IN_CSV_FIELDS = (
    "name",
    "line1",
    "rr_type1",
    "val1",
    "line2",
    "rr_type2",
    "val2",
)
OUT_CSV_FIELDS = (
    "dataset",
    "input_file",
    "line",
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
)


def convert_rr_data(rr_type, rr_data):
    if rr_type in [CNAME, DNAME, NS]:
        type_name = RdataType(rr_type).name.lower()
        yield f"dns.{type_name}", decode_name(rr_data)
    elif rr_type in [NSEC]:
        yield "dns.nsec.next_domain_name", decode_name(rr_data.split()[0])
    elif rr_type in [SOA]:
        data = rr_data.split()
        yield "dns.soa.mname", decode_name(data[0])
        yield "dns.soa.rname", decode_name(data[1])
    else:
        assert False, f"{rr_type} not supported"


def write_row(writer, out_csvfile, row):
    writer.writerow(row)
    out_csvfile.flush()


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--header", action="store_true", help="Print header and exit")
    argparser.add_argument("input_filename", type=pathlib.Path)
    args = argparser.parse_args()
    input_filename = args.input_filename.absolute().relative_to(INPUT_DATASETS)
    in_csvfile = sys.stdin
    reader = csv.DictReader(in_csvfile, delimiter="\t", quoting=csv.QUOTE_NONE, fieldnames=IN_CSV_FIELDS)
    out_csvfile = sys.stdout
    writer = csv.DictWriter(out_csvfile, delimiter=",", fieldnames=OUT_CSV_FIELDS)
    if args.header:
        writer.writeheader()
        return
    out_csvfile.flush()
    for row in reader:
        try:
            if row["line1"] == "LINE":
                # skip original header
                continue
            if row["line1"] == row["line2"]:
                # skip same occurrence
                continue
            if not row["rr_type1"] or not row["rr_type2"]:
                print("Error: No pair in", row, file=sys.stderr)
                continue
            for rr_field1, rr_name1 in convert_rr_data(int(row["rr_type1"]), row["val1"]):
                for rr_field2, rr_name2 in convert_rr_data(
                    int(row["rr_type2"]), row["val2"]
                ):
                    resp_name = decode_name(row["name"])
                    csb, ccsb = common_suffixes(resp_name, rr_name1)
                    write_row(
                        writer,
                        out_csvfile,
                        {
                            "dataset": "secspider",
                            "input_file": str(input_filename),
                            "line": row["line1"],
                            "protocol": "dns",
                            "msg": "r",
                            "qtype": "?",
                            "Field x": "dns.resp.name",
                            "Field y": rr_field1,
                            "Name x": resp_name,
                            "Name y": rr_name1,
                            "Same Name": int(resp_name == rr_name1),
                            "Common Suffix Bytes": csb,
                            "Common Component Suffix Bytes": ccsb,
                        },
                    )
                    csb, ccsb = common_suffixes(resp_name, rr_name2)
                    write_row(
                        writer,
                        out_csvfile,
                        {
                            "dataset": "secspider",
                            "input_file": str(input_filename),
                            "line": row["line2"],
                            "protocol": "dns",
                            "msg": "r",
                            "qtype": "?",
                            "Field x": "dns.resp.name",
                            "Field y": rr_field2,
                            "Name x": resp_name,
                            "Name y": rr_name2,
                            "Same Name": int(resp_name == rr_name2),
                            "Common Suffix Bytes": csb,
                            "Common Component Suffix Bytes": ccsb,
                        },
                    )
                    csb, ccsb = common_suffixes(rr_name1, rr_name2)
                    write_row(
                        writer,
                        out_csvfile,
                        {
                            "dataset": "secspider",
                            "input_file": str(input_filename),
                            "line": f"{row['line1']}|{row['line2']}",
                            "protocol": "dns",
                            "msg": "r",
                            "qtype": "?",
                            "Field x": rr_field1,
                            "Field y": rr_field2,
                            "Name x": rr_name1,
                            "Name y": rr_name2,
                            "Same Name": int(rr_name1 == rr_name2),
                            "Common Suffix Bytes": csb,
                            "Common Component Suffix Bytes": ccsb,
                        },
                    )
        except Exception as e:
            print("Error:", e, "on", row, file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
