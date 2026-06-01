#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import collections
import csv
import json
import os
import pathlib
import pprint
import sys
import traceback

from dns.rdatatype import (
    # A,
    # AAAA,
    # CAA,
    CNAME,
    DNAME,
    NS,
    NSEC,
    # NSEC3,
    # RRSIG,
    SOA,
    # TLSA,
    # TXT,
    RdataType,
)

from cbor4dns_utils import decode_name, common_suffixes


SCRIPT_PATH = pathlib.Path(__file__).resolve().parent
INPUT_DATASETS = pathlib.Path(
    os.environ.get("INPUT_DATASETS", SCRIPT_PATH / "input_datasets")
)
CSV_FIELDS = (
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


def collect_rr_name(rr):
    # if rr["type"] in [A, AAAA]:
    #     yield rr["type"].name, ipaddress.ip_address(rr["data"]).packed.hex()
    rr_name = decode_name(rr["name"])
    yield "dns.resp.name", rr_name
    if rr["type"] in [CNAME, DNAME, NS]:
        type_name = RdataType(rr["type"]).name.lower()
        yield f"dns.{type_name}", decode_name(rr["data"])
    elif rr["type"] in [NSEC]:
        yield "dns.nsec.next_domain_name", decode_name(rr["data"].split()[0])
    elif rr["type"] in [SOA]:
        data = rr["data"].split()
        yield "dns.soa.mname", decode_name(data[0])
        yield "dns.soa.rname", decode_name(data[1])
    # TODO CAA records?


def collect_dns_json(dns_json):
    question = dns_json.get("Question", [])
    if len(question) > 1:
        print("==== >1 Question!")
        pprint.pprint(dns_json)
        print("----")
    qtype = None
    for rr in question:
        qtype = RdataType(rr["type"]).name
        yield qtype, "dns.qry.name", decode_name(rr["name"])
    for rr in (
        dns_json.get("Answer", [])
        + dns_json.get("Authority", [])
        + dns_json.get("Additional", [])
    ):
        for rr_type, rr_name in collect_rr_name(rr):
            if rr_type is not None and rr_name is not None:
                yield qtype, rr_type, rr_name


def collect_json(line_file, line_nr, line):
    try:
        d = json.loads(line, object_pairs_hook=collections.OrderedDict)
        res = []
        tranco_name = decode_name(d["domain"])
        for redirect_name, value in d["genesis"]["redirected"]["chains"].items():
            redirect_name = decode_name(redirect_name)
            csb, ccsb = common_suffixes(tranco_name, redirect_name)
            res.append(
                {
                    "dataset": "tls",
                    "input_file": str(line_file),
                    "line": line_nr,
                    "protocol": "http",
                    "Field x": "tranco_base",
                    "Field y": "redirect",
                    "Name x": tranco_name,
                    "Name y": redirect_name,
                    "Same Name": int(tranco_name == redirect_name),
                    "Common Suffix Bytes": csb,
                    "Common Component Suffix Bytes": ccsb,
                }
            )
            for record, dns_json in value["dns"].items():
                if dns_json is None:
                    continue
                dns_names = list(collect_dns_json(dns_json))
                for i1, (qtype1, rtype1, name1) in enumerate(dns_names):
                    csb, ccsb = common_suffixes(tranco_name, name1)
                    res.append(
                        {
                            "dataset": "tls",
                            "input_file": str(line_file),
                            "line": line_nr,
                            "protocol": "assoc",
                            "msg": "r",
                            "qtype": qtype1,
                            "Field x": "tranco_base",
                            "Field y": rtype1,
                            "Name x": tranco_name,
                            "Name y": name1,
                            "Same Name": int(tranco_name == name1),
                            "Common Suffix Bytes": csb,
                            "Common Component Suffix Bytes": ccsb,
                        }
                    )
                    csb, ccsb = common_suffixes(redirect_name, name1)
                    res.append(
                        {
                            "dataset": "tls",
                            "input_file": str(line_file),
                            "line": line_nr,
                            "protocol": "assoc",
                            "msg": "r",
                            "qtype": qtype1,
                            "Field x": "redirect",
                            "Field y": rtype1,
                            "Name x": redirect_name,
                            "Name y": name1,
                            "Same Name": int(redirect_name == name1),
                            "Common Suffix Bytes": csb,
                            "Common Component Suffix Bytes": ccsb,
                        }
                    )
                    for i2, (qtype2, rtype2, name2) in enumerate(dns_names[i1:]):
                        assert qtype1 == qtype2
                        if rtype1 == rtype2:
                            # skip duplicate occurrences
                            continue
                        csb, ccsb = common_suffixes(name1, name2)
                        res.append(
                            {
                                "dataset": "tls",
                                "input_file": str(line_file),
                                "line": line_nr,
                                "protocol": "dns",
                                "msg": "r",
                                "qtype": qtype1,
                                "Field x": rtype1,
                                "Field y": rtype2,
                                "Name x": name1,
                                "Name y": name2,
                                "Same Name": int(name1 == name2),
                                "Common Suffix Bytes": csb,
                                "Common Component Suffix Bytes": ccsb,
                            }
                        )
        return res
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print("Error:", e, "on", line_nr, line, file=sys.stderr)
        return []


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--header", action="store_true", help="Print header and exit")
    args = argparser.parse_args()
    out_csvfile = sys.stdout
    writer = csv.DictWriter(out_csvfile, delimiter=",", fieldnames=CSV_FIELDS)
    if args.header:
        writer.writeheader()
        return
    out_csvfile.flush()
    for line in sys.stdin:
        line_comps = line.split("\t")
        if len(line_comps) < 3:
            continue
        line_file = pathlib.Path(line_comps[0]).absolute()
        try:
            line_file = line_file.relative_to(INPUT_DATASETS)
        except ValueError:
            pass
        line_nr = int(line_comps[1])
        line = "\t".join(line_comps[2:])
        result = collect_json(line_file, line_nr, line)
        writer.writerows(result)
        out_csvfile.flush()


if __name__ == "__main__":
    main()
