#! /usr/bin/env python3
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import collections
import csv
import multiprocessing
import os
import pathlib
import subprocess
import sys
import traceback

import bounded_pool_executor

import cbor4dns_utils


SCRIPT_PATH = pathlib.Path(__file__).resolve().parent
INPUT_DATASETS = SCRIPT_PATH / "input_datasets"
FIELDS = [
    "frame.number",
    "frame.protocols",
    "_ws.col.Source",
    "_ws.col.Destination",
    "dns.flags.response",
    "dns.qry.type",
    "dns.resp.type",
    "dns.retransmit_response_in",
    "dns.response_to",
    "udp.payload",
    "tcp.reassembled.data",
    "tcp.payload",
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
QUERIES = None
RESPONSES = None
WRITER = None
DATASET = None


def rewrite_row(row):
    global DATASET, QUERIES, RESPONSES, WRITER
    row.update(DATASET)
    try:
        if not row["udp.payload"] and not row["tcp.reassembled.data"]:
            row["payload"] = row["tcp.payload"][4:]
        elif not row["udp.payload"]:
            row["payload"] = row["tcp.reassembled.data"][4:]
        else:
            row["payload"] = row["udp.payload"]
        row.pop("udp.payload", None)
        row.pop("tcp.reassembled.data", None)
        row.pop("tcp.payload", None)
        frame_number = int(row["frame.number"])
        if row["dns.flags.response"] == "True" or row["dns.flags.response"] == "1":
            if row["dns.retransmit_response_in"]:
                retransmit_response_in = int(row["dns.retransmit_response_in"])
                try:
                    if (
                        retransmit_response_in in RESPONSES
                        and RESPONSES[retransmit_response_in] in QUERIES
                    ):
                        row["dns.query_payload"] = QUERIES[
                            RESPONSES[retransmit_response_in]
                        ]
                except KeyError as e:
                    print(traceback.format_exc(), file=sys.stderr)
                    print("Error:", e, "on", row, file=sys.stderr)
                row["qr-diff"] = (
                    f"{frame_number - retransmit_response_in}|"
                    f"{frame_number - RESPONSES.get(retransmit_response_in, 0)}"
                )
            if row["dns.response_to"]:
                response_to = int(row["dns.response_to"])
                RESPONSES[frame_number] = response_to
                if response_to in QUERIES:
                    try:
                        row["dns.query_payload"] = QUERIES[response_to]
                    except KeyError as e:
                        print(traceback.format_exc(), file=sys.stderr)
                        print("Error:", e, "on", row, file=sys.stderr)
                row["qr-diff"] = f"{frame_number - response_to}"
            row["stored"] = len(RESPONSES)
        else:
            QUERIES[frame_number] = row["payload"]
            row["stored"] = len(QUERIES)
        WRITER.writerow(row)
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print("Error:", e, "on", row, file=sys.stderr)
        sys.stderr.flush()


def main():
    global DATASET, QUERIES, RESPONSES, WRITER
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--start-frame", help="Start parsing PCAP file at this frame",
                        type=int, default=0)
    parser.add_argument(metavar="<Input PCAP filename>", dest="pcap")
    args = parser.parse_args()

    # use maximum possible size for field size
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = (max_int >> 2)

    try:
        pcap = pathlib.Path(args.pcap).absolute().relative_to(INPUT_DATASETS)
    except ValueError:
        pcap = args.pcap
    DATASET = {
        "pcap": pcap,
        "dataset": f"tranco{os.environ.get('EXP', '')}",
    }
    process = subprocess.Popen(
        [
            "tshark",
            "-Y",
            f"frame.number > {args.start_frame} && dns.count.queries == 1 && !vlan",
            "-r",
            args.pcap,
            "-Tfields",
            "-E",
            "aggregator=|",
            # "-E",
            # "separator=;",
        ]
        # combine FIELDS with '-e'
        + [a for pair in [("-e", f) for f in FIELDS] for a in pair],
        stdout=subprocess.PIPE,
        text=True,
    )
    reader = csv.DictReader(
        process.stdout, delimiter="\t", quoting=csv.QUOTE_NONE, fieldnames=FIELDS
    )
    out_csvfile = sys.stdout
    manager = multiprocessing.Manager()
    QUERIES = cbor4dns_utils.EmptyingDict(manager)
    RESPONSES = cbor4dns_utils.EmptyingDict(manager)
    WRITER = cbor4dns_utils.FlushableThreadSafeDictWriter(
        out_csvfile,
        manager,
        delimiter=";",
        fieldnames=["dataset", "pcap"]
        + [
            f if f != "udp.payload" else "payload"
            for f in FIELDS
            if f not in ["tcp.reassembled.data", "tcp.payload"]
        ]
        + ["dns.query_payload", "qr-diff", "stored"],
    )
    WRITER.writeheader()
    with bounded_pool_executor.BoundedThreadPoolExecutor(
        max_workers=multiprocessing.cpu_count()
    ) as executor:
        try:
            for row in reader:
                executor.submit(rewrite_row, row)
        except csv.Error as e:
            print(traceback.format_exc(), file=sys.stderr)
            print("Error:", e, "after", row, file=sys.stderr)
            sys.stderr.flush()


if __name__ == "__main__":
    main()
