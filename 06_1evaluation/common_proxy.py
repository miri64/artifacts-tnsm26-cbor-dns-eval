#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.

import csv
import io
import json
import logging
import sys
import time

import cbor2


if "/cbor4dns" not in sys.path:
    sys.path.append("/cbor4dns")

import cbor4dns.decode
import cbor4dns.encode


def dns_dumps(byts, query=None, packed=False):
    with io.BytesIO() as cbor_file:
        try:
            cbor4dns.encode.Encoder(
                cbor_file, packed=packed, always_omit_question=False
            ).encode(byts, query)
        except RecursionError:
            logging.error(f"Recursion error caused by {byts!r} (query: {query!r}, packed: {packed})")
            raise

        return cbor_file.getvalue()


def dns_query_loads(byts):
    with io.BytesIO() as cbor_file:
        res = cbor4dns.decode.Decoder(cbor_file).decode(
            cbor4dns.decode.MsgType.QUERY,
            obj=cbor2.loads(byts),
        )

        return res.to_wire(want_shuffle=False)


def dns_response_loads(byts, query=None, packed=False):
    with io.BytesIO() as cbor_file:
        res = cbor4dns.decode.Decoder(cbor_file).decode(
            cbor4dns.decode.MsgType.RESPONSE,
            orig_query=query,
            packed=packed,
            obj=cbor2.loads(byts),
        )
        return res.to_wire(want_shuffle=False)


class CommonProxy:
    def __init__(self):
        self.csvfile = None
        self.proxy = None
        self.domain = None
        self.domain_rank = None
        self.run = None
        self.convert = True
        self.writer = None
        self.lhts = None
        self.dns_requests = {}
        self.packed = False

    def _start_dict_writer(self):
        if self.csvfile is None or self.writer is not None:
            return
        self.writer = csv.DictWriter(
            self.csvfile,
            delimiter="\t",
            fieldnames=[
                "timestamp",
                "proxy",
                "domain",
                "domain_rank",
                "run",
                "convert",
                "packed",
                "lhts",
                "url",
                "method",
                "response_status",
                "host",
                "date",
                "orig_content_type",
                "orig_content_encoding",
                "orig_body_length",
                "orig_content_length",
                "orig_body_hex",
                "new_content_type",
                "new_body_length",
                "new_body_hex",
                "query_missing",
                "handler_time",
                "msg",
            ]
        )

    def _write_row(self, row, start=None):
        row["timestamp"] = time.time()
        if start is not None:
            row["handler_time"] = time.time() - start
        self.writer.writerow(row)
        self.csvfile.flush()

    def _write_marker(self, flow):
        try:
            if flow.request.method == "POST":
                obj = json.loads(flow.request.raw_content)
                if isinstance(obj, dict) and obj.get("marker", False):
                    if obj["signal"] == "start":
                        self.domain = obj["domain"]
                        self.domain_rank = obj["rank"]
                        self.run = obj["run"]
                        self.convert = obj["convert"]
                        self.packed = obj["packed"]
                        self.lhts = obj["lhts"]
                        self._write_row(
                            {
                                "proxy": self.proxy,
                                "domain": self.domain,
                                "domain_rank": self.domain_rank,
                                "convert": self.convert,
                                "packed": self.packed,
                                "lhts": self.lhts,
                                "run": self.run,
                                "url": flow.request.url,
                                "host": flow.request.headers.get("host"),
                                "msg": f"Start run"
                            }
                        )
                    elif obj["signal"] == "end":
                        self._write_row(
                            {
                                "proxy": self.proxy,
                                "domain": self.domain,
                                "domain_rank": self.domain_rank,
                                "convert": self.convert,
                                "packed": self.packed,
                                "lhts": self.lhts,
                                "run": self.run,
                                "url": flow.request.url,
                                "host": flow.request.headers.get("host"),
                                "msg": f"End run"
                            }
                        )
                        self.convert = None
                        self.domain = None
                        self.domain_rank = None
                        self.run = None
                        self.packed = None
                        self.lhts = None
                    self.csvfile.flush()
                    return True
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return False

    def _prefill_flow_row(self, flow):
        return {
            "proxy": self.proxy,
            "domain": self.domain,
            "domain_rank": self.domain_rank,
            "run": self.run,
            "convert": self.convert,
            "packed": self.packed,
            "lhts": self.lhts,
            "url": flow.request.url,
            'method': flow.request.method,
            "host": flow.request.headers.get("host"),
        }

    def _not_converted(self, flow, msg):
        row = self._prefill_flow_row(flow)
        row.update(
            {
                "response_status": (
                    msg.status_code if hasattr(msg, "status_code") else None
                ),
                "date": msg.headers.get("date"),
                "orig_content_type": msg.headers.get("content-type"),
                "orig_content_encoding": msg.headers.get(
                    "content-encoding"
                ),
                "orig_body_length": len(msg.raw_content),
                "orig_content_length": msg.headers.get(
                    "content-length"
                ),
                "msg": "Not converted"
            }
        )
        return row

    def _exc(self, flow, msg, exc):
        row = self._prefill_flow_row(flow)
        row.update(
            {
                "response_status": (
                    msg.status_code if hasattr(msg, "status_code") else None
                ),
                "date": msg.headers.get("date"),
                "orig_content_type": msg.headers.get("content-type"),
                "orig_content_encoding": msg.headers.get(
                    "content-encoding"
                ),
                "orig_body_length": len(msg.raw_content),
                "orig_content_length": msg.headers.get("content-length"),
                "msg": f"error: {type(exc).__name__}",
            }
        )
        return row

    def _cbor2dns(self, flow, msg):
        content_type = msg.headers.get("content-type", "")
        if flow.response == msg:
            assert "application/dns+cbor" == flow.request.headers.get(
                "content-type", "",
            )
            dns_obj = dns_response_loads(
                msg.raw_content,
                flow.request.raw_content,
                ";packed=1" in content_type
            )
        else:
            dns_obj = dns_query_loads(
                msg.raw_content,
            )
            self.dns_requests[flow.id] = msg.raw_content
        content_len = msg.headers.get("content-length", "")
        content = msg.raw_content
        msg.raw_content = dns_obj
        msg.headers["content-type"] = "application/dns-message"
        msg.headers["content-length"] = str(len(dns_obj))
        row = self._prefill_flow_row(flow)
        row.update(
            {
                "response_status": (
                    msg.status_code if hasattr(msg, "status_code") else None
                ),
                "date": msg.headers.get("date"),
                "orig_content_type": content_type,
                "orig_content_encoding": msg.headers.get(
                    "content-encoding"
                ),
                "orig_body_length": len(content),
                "orig_content_length": content_len,
                "orig_body_hex": content.hex(),
                "new_content_type": "application/dns-message",
                "new_body_length": len(dns_obj),
                "new_body_hex": dns_obj.hex(),
                "msg": "Converted CBOR to DNS",
            }
        )
        return row

    def _dns2cbor(self, flow, msg):
        query_missing = None
        if flow.response == msg:
            if "application/dns+cbor" == flow.request.headers.get(
                "content-type", "",
            ):
                query = flow.request.raw_content
            elif "application/dns-message" == flow.request.headers.get(
                "content-type", "",
            ):
                try:
                    query = self.dns_requests[flow.id]
                    del self.dns_requests[flow.id]
                except KeyError:
                    logging.error(
                        f"{flow.id!r} not in {self.dns_requests}. "
                        "Compressing without query."
                    )
                    query = None
                    query_missing = True
            else:
                assert False, "Unable to find original request"
            cbor_obj = dns_dumps(
                msg.raw_content,
                query=query,
                packed=self.packed,
            )
        else:
            cbor_obj = dns_dumps(msg.raw_content, packed=self.packed)
        content_type = msg.headers.get("content-type", "")
        content_len = msg.headers.get("content-length", "")
        content = msg.raw_content
        if self.convert:
            msg.raw_content = cbor_obj
            msg.headers["content-type"] = "application/dns+cbor"
            if  self.packed and flow.response == msg:
                msg.headers["content-type"] += ";packed=1"
            msg.headers["content-length"] = str(len(cbor_obj))
        row = self._prefill_flow_row(flow)
        row.update(
            {
                "response_status": (
                    msg.status_code if hasattr(msg, "status_code") else None
                ),
                "date": msg.headers.get("date"),
                "orig_content_type": content_type,
                "orig_content_encoding": msg.headers.get(
                    "content-encoding"
                ),
                "orig_body_length": len(content),
                "orig_content_length": content_len,
                "orig_body_hex": content.hex(),
                "new_content_type": "application/dns+cbor",
                "new_body_length": len(cbor_obj),
                "new_body_hex": cbor_obj.hex(),
                "query_missing": query_missing,
                "msg": "Converted DNS to CBOR" if self.convert else "Not converted",
            }
        )
        return row

    def _cbor2json(self, flow, msg):
        obj = cbor2.loads(msg.raw_content)
        json_obj = json.dumps(obj).encode()
        content_type = msg.headers.get("content-type", "")
        content_len = msg.headers.get("content-length", "")
        content = msg.raw_content
        msg.raw_content = json_obj
        msg.headers["content-type"] = "application/json"
        msg.headers["content-length"] = str(len(json_obj))
        row = self._prefill_flow_row(flow)
        row.update(
            {
                "response_status": (
                    msg.status_code if hasattr(msg, "status_code") else None
                ),
                "date": msg.headers.get("date"),
                "orig_content_type": content_type,
                "orig_content_encoding": msg.headers.get(
                    "content-encoding"
                ),
                "orig_body_length": len(content),
                "orig_content_length": content_len,
                "orig_body_hex": content.hex(),
                "new_content_type": "application/json",
                "new_body_length": len(json_obj),
                "new_body_hex": json_obj.hex(),
                "msg": "Converted CBOR to JSON",
            }
        )
        return row

    def _json2cbor(self, flow, msg):
        try:
            obj = json.loads(msg.raw_content)
            if isinstance(obj, (dict, list)):
                cbor_obj = cbor2.dumps(obj)
                content_type = msg.headers.get("content-type", "")
                content_len = msg.headers.get("content-length", "")
                content = msg.raw_content
                if self.convert:
                    msg.raw_content = cbor_obj
                    msg.headers["content-type"] = "application/cbor"
                    msg.headers["content-length"] = str(len(cbor_obj))
                row = self._prefill_flow_row(flow)
                row.update(
                    {
                        "response_status": (
                            msg.status_code if hasattr(msg, "status_code") else None
                        ),
                        "date": msg.headers.get("date"),
                        "orig_content_type": content_type,
                        "orig_content_encoding": msg.headers.get(
                            "content-encoding"
                        ),
                        "orig_body_length": len(content),
                        "orig_content_length": content_len,
                        "orig_body_hex": content.hex(),
                        "new_content_type": "application/cbor",
                        "new_body_length": len(cbor_obj),
                        "new_body_hex": cbor_obj.hex(),
                        "msg": "Converted JSON to CBOR" if self.convert else "Not converted",
                    }
                )
            else:
                row = self._not_converted(flow, msg)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            row = self._exc(flow, msg, exc)
        return row
