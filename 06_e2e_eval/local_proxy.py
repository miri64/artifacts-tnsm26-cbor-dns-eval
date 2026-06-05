#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.

import os
import logging
import pathlib
import time

import common_proxy


PROXY_LOG = os.environ.get("PROXY_LOG", "/app/output-dataset/mitmproxy-local.log")


class LocalProxy(common_proxy.CommonProxy):
    def __init__(self):
        super().__init__(pathlib.Path(PROXY_LOG), "local")

    def request(self, flow):
        start = time.time()
        try:
            if self._write_marker(flow):
                return
            if self.convert is None:
                logging.info("Ignoring %r", flow.request)
                return
            content_type = flow.request.headers.get("content-type", "")
            if content_type == "application/dns-message":
                row = self._dns2cbor(flow, flow.request)
            elif (
                flow.request.method in ["POST", "PUT"]
                and "json" in content_type
                and not flow.request.headers.get("content-encoding")
            ):
                row = self._json2cbor(flow, flow.request)
            else:
                row = self._not_converted(flow, flow.request)
        except Exception as exc:
            row = self._exc(flow, flow.request, exc)
        self._write_row(row, start)

    def response(self, flow):
        start = time.time()
        try:
            if self.convert is None:
                logging.info("Ignoring %r", flow.response)
                return
            content_type = flow.response.headers.get("content-type", "")
            if content_type.startswith("application/dns+cbor"):
                row = self._cbor2dns(flow, flow.response)
            elif "x-to-cbor" in flow.response.headers:
                row = self._cbor2json(flow, flow.response)
            else:
                row = self._not_converted(flow, flow.response)
        except Exception as exc:
            row = self._exc(flow, flow.response, exc)
        self._write_row(row, start)


addons = [LocalProxy()]
