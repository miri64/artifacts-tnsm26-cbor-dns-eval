#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.

import logging
import os
import pathlib
import time

import common_proxy


PROXY_LOG = os.environ.get("PROXY_LOG", "/app/output-dataset/mitmproxy-local.log")


class LocalProxy(common_proxy.CommonProxy):
    def __init__(self):
        super().__init__()
        csvpath = pathlib.Path(PROXY_LOG)
        if csvpath.exists():
            self.csvfile = csvpath.open("at")
            self._start_dict_writer()
        else:
            self.csvfile = csvpath.open("wt")
            self._start_dict_writer()
            self.writer.writeheader()
        self.proxy = "local"
        self.domain = None
        self.run = None
        self.convert = None

    def request(self, flow):
        start = time.time()
        if self._write_marker(flow):
            return
        if self.convert is None:
            return
        content_type = flow.request.headers.get("content-type", "")
        if content_type == "application/dns-message":
            logging.info("Content-TYPE! %s", content_type)
            row = self._dns2cbor(flow, flow.request)
        elif (
            flow.request.method in ["POST", "PUT"]
            and "json" in content_type
            and not flow.request.headers.get("content-encoding")
        ):
            row = self._json2cbor(flow, flow.request)
        else:
            row = self._not_converted(flow, flow.request)
        self._write_row(row, start)

    def response(self, flow):
        start = time.time()
        if self.convert is None:
            return
        content_type = flow.response.headers.get("content-type", "")
        if content_type.startswith("application/dns+cbor"):
            row = self._cbor2dns(flow, flow.response)
        elif content_type == "application/cbor":
            row = self._cbor2json(flow, flow.response)
        else:
            row = self._not_converted(flow, flow.response)
        self._write_row(row, start)


addons = [LocalProxy()]
