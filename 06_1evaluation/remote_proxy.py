#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.

import gzip
import os
import pathlib
import time

import common_proxy


PROXY_LOG = os.environ.get("PROXY_LOG", "/app/output-dataset/mitmproxy-remote.log")


class RemoteProxy(common_proxy.CommonProxy):
    def __init__(self):
        super().__init__()

        if PROXY_LOG.endswith(".csv.gz"):
            open_func = gzip.open
        else:
            open_func = open
        if pathlib.Path(PROXY_LOG).exists():
            self.csvfile = open_func(PROXY_LOG, "at")
            self._start_dict_writer()
        else:
            self.csvfile = open_func(PROXY_LOG, "wt")
            self._start_dict_writer()
            self.writer.writeheader()
        self.proxy = "remote"

    def request(self, flow):
        start = time.time()
        if self._write_marker(flow):
            flow.intercept()
            return
        if self.convert is None:
            return
        if flow.request.headers.get("content-type") == "application/dns+cbor":
            row = self._cbor2dns(flow, flow.request)
        elif (
            flow.request.method in ["POST", "PUT"]
            and flow.request.headers.get("content-type") == "application/cbor"
        ):
            row = self._cbor2json(flow, flow.request)
        else:
            row = self._not_converted(flow, flow.request)
        self._write_row(row, start)

    def response(self, flow):
        start = time.time()
        if self.convert is None:
            return
        if flow.response.headers.get("content-type") == "application/dns-message":
            row = self._dns2cbor(flow, flow.response)
        else:
            row = self._json2cbor(flow, flow.response)
        self._write_row(row, start)


addons = [RemoteProxy()]
