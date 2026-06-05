#!/usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024-26 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import io
import os
import pathlib
import subprocess
import sys
import timeit

import cbor2
import dns.message
import dns.name
import dns.rdatatype

SCRIPT_PATH = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
CBOR4DNS_PATH = str((SCRIPT_PATH / ".." / "04_cbor4dns_eval" / "cbor4dns").resolve())
TAXONOMY_PATH = str((SCRIPT_PATH / "..").resolve())

if CBOR4DNS_PATH not in sys.path:
    sys.path.append(CBOR4DNS_PATH)
import cbor4dns.encode
import cbor4dns.decode

if TAXONOMY_PATH not in sys.path:
    sys.path.append(TAXONOMY_PATH)
from utils import taxonomy

INPUT_FIELDNAMES = [
    "dataset",
    "pcap",
    "frame.number",
    "frame.protocols",
    "_ws.col.Source",
    "_ws.col.Destination",
    "dns.flags.response",
    "dns.qry.type",
    "dns.resp.type",
    "dns.retransmit_response_in",
    "dns.response_to",
    "payload",
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
    "dns.query_payload",
    "qr-diff",
    "stored",
]
MSG_TYPES = {
    "q": cbor4dns.decode.MsgType.QUERY,
    "r": cbor4dns.decode.MsgType.RESPONSE,
}


def dns_encode(dns_msg):
    return dns_msg.to_wire(want_shuffle=False)


def dns_decode(dns_bin):
    return dns.message.from_wire(dns_bin)


def cbor_encode(encoder, dns_msg, orig_query=None):
    encoder.fp.seek(0)
    encoder.encode(dns_msg, orig_query)


def cbor_decode(decoder, msg_type, packed, orig_query=None):
    decoder.fp.seek(0)
    return decoder.decode(msg_type, orig_query=orig_query, packed=packed)


def cbor_encode_to_bytes(dns_msg, packed, orig_query=None):
    with io.BytesIO() as cbor_file:
        encoder = cbor4dns.encode.Encoder(
            cbor_file,
            packed=packed,
            always_omit_question=False,
        )
        cbor_encode(encoder, dns_msg, orig_query)
        return cbor_file.getvalue()


def main():
    TAG_TYPE = ""
    PACKED_VAL = 1
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-i", "--iterations", type=int, required=True)
    argparser.add_argument("--header", action="store_true")
    measure_group = argparser.add_mutually_exclusive_group(required=False)
    measure_group.add_argument("-d", "--measure-dns", action="store_true")
    measure_group.add_argument("-p", "--measure-packed", action="store_true")
    if hasattr(cbor4dns.encode, "RefIdx"):
        argparser.add_argument(
            "-t",
            "--tag",
            type=int,
            required=True,
            help="Tag number for name compression referencing",
        )
    args = argparser.parse_args()

    measure_dns = args.measure_dns
    measure_packed = args.measure_packed
    cols = {}
    git_branch = subprocess.check_output(
        ["git", "-C", str(CBOR4DNS_PATH), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
    ).strip()
    if git_branch == "packed-lite":
        if not args.measure_packed:
            assert git_branch != "packed-lite", (
                "On packed-lite branch, but not measuring packed. Set -p flag."
            )
        PACKED_VAL = "lite"
        measure_dns = False
    if hasattr(cbor4dns.encode, "RefIdx"):
        if args.measure_dns:
            assert not hasattr(cbor4dns.encode, "RefIdx"), (
                "On name-compr-str-ref branch, but measuring DNS. Unset -d flag."
            )
        if args.measure_packed:
            assert not hasattr(cbor4dns.encode, "RefIdx"), (
                "On name-compr-str-ref branch, but measuring packed. Unset -p flag."
            )
        cbor4dns.encode.RefIdx.tag = args.tag
        TAG_TYPE = f" t{args.tag}"
        measure_dns = False
        measure_packed = False
    fieldnames = [
        "dataset",
        "pcap",
        "frame",
        "protocol",
        "msg",
        "qtype",
        "w_query",
        "iterations",
    ]
    if measure_dns:
        cols["dns"] = {
            "decode": "application/dns-message decode",
            "encode": "application/dns-message encode",
        }
        fieldnames.extend(sorted(cols["dns"].values()))
    if PACKED_VAL != "lite" and (not measure_packed and not measure_dns):
        cols["cbor_base"] = {
            "decode": f"application/cbor+dns{TAG_TYPE} decode",
            "encode": f"application/cbor+dns{TAG_TYPE} encode",
        }
        fieldnames.extend(sorted(cols["cbor_base"].values()))
    if measure_packed:
        cols["cbor_packed"] = {
            "decode": f"application/cbor+dns;packed={PACKED_VAL}{TAG_TYPE} decode",
            "encode": f"application/cbor+dns;packed={PACKED_VAL}{TAG_TYPE} encode",
        }
        fieldnames.extend(sorted(cols["cbor_packed"].values()))
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=fieldnames,
    )
    reader = csv.DictReader(
        sys.stdin,
        fieldnames=INPUT_FIELDNAMES,
        delimiter=";",
    )

    if args.header:
        writer.writeheader()
        return
    for in_row in reader:
        try:
            dns_bin = bytes.fromhex(in_row["payload"])
        except ValueError:
            continue
        try:
            dns_msg = dns.message.from_wire(dns_bin)
        except dns.name.BadLabelType as e:
            print(f"{e} for {dns_bin.hex()}", file=sys.stderr)
            continue
        cbor_base_bin = cbor_encode_to_bytes(dns_msg, packed=False)
        tax = taxonomy.main(cbor2.loads(cbor_base_bin))

        if (
            tax[0] == "tier 1"
            and tax[1] in ["binary", "textual"]
            and tax[2] == "non-redundant"
            and tax[3] == "flat"
        ):
            out_row = {
                "dataset": in_row["dataset"],
                "pcap": in_row["pcap"],
                "frame": in_row["frame.number"],
                "protocol": in_row["frame.protocols"].split(":")[-1],
                "msg": "r" if in_row["dns.flags.response"] in ["1", "True"] else "q",
                "iterations": args.iterations,
            }
            if "dns" not in cols and "cbor_base" not in cols and out_row["msg"] == "q":
                # packed only applies for responses
                continue
            if "dns" in cols:
                out_row[cols["dns"]["encode"]] = timeit.timeit(
                    lambda: dns_encode(dns_msg),
                    number=args.iterations,
                )
                out_row[cols["dns"]["decode"]] = timeit.timeit(
                    lambda: dns_decode(dns_bin),
                    number=args.iterations,
                )
            if "cbor_base" in cols or "cbor_packed" in cols:
                if in_row.get("dns.query_payload"):
                    with io.BytesIO() as cbor_query_file:
                        cbor_query_encoder = cbor4dns.encode.Encoder(
                            cbor_query_file, packed=False, always_omit_question=False
                        )
                        cbor_query_encoder.encode(
                            bytes.fromhex(in_row["dns.query_payload"])
                        )
                        orig_query = cbor_query_file.getvalue()
                else:
                    orig_query = None
                out_row["w_query"] = orig_query is not None
                for format, packed in [("cbor_base", False), ("cbor_packed", True)]:
                    if packed:
                        cbor_bin = cbor_encode_to_bytes(
                            dns_msg, packed=packed, orig_query=orig_query
                        )
                    else:
                        cbor_bin = cbor_base_bin
                    if format in cols:
                        with io.BytesIO() as cbor_file:
                            encoder = cbor4dns.encode.Encoder(
                                cbor_file,
                                packed=packed,
                                always_omit_question=False,
                            )
                            out_row[cols[format]["encode"]] = timeit.timeit(
                                lambda: cbor_encode(
                                    encoder, dns_msg, orig_query=orig_query
                                ),
                                number=args.iterations,
                            )
                        with io.BytesIO(cbor_bin) as cbor_file:
                            decoder = cbor4dns.decode.Decoder(
                                cbor_file,
                            )
                            try:
                                out_row[cols[format]["decode"]] = timeit.timeit(
                                    lambda: cbor_decode(
                                        decoder,
                                        MSG_TYPES[out_row["msg"]],
                                        packed=packed,
                                        orig_query=orig_query,
                                    ),
                                    number=args.iterations,
                                )
                            except Exception as e:
                                print(
                                    f"\"{e}\" for \"{cbor_bin.hex()}\" "
                                    f"({msg_type}, {packed}, {orig_query.hex()})",
                                    file=sys.stderr
                                )
            for query_type in in_row["dns.qry.type"].split("|"):
                type_name = dns.rdatatype.RdataType(int(query_type)).name
                out_row["qtype"] = type_name
                writer.writerow(out_row)
                sys.stdout.flush()


if __name__ == "__main__":
    main()
