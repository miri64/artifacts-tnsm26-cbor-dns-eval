#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.


import argparse
import asyncio
import io
import pathlib
import sqlite3
import socket
import sys
import time
import timeit

import dns.asyncbackend
import dns.message
import dns.inet
import httpx
import ssl
import tornado

from typing import Optional, Union

from dns.query import (
    have_doh,
)
from scapy.all import DNS as ScapyDNS


SCRIPT_PATH = pathlib.Path(__file__).parent
CBOR4DNS_PATH = (SCRIPT_PATH / ".." / "04_cbor4dns_eval" / "cbor4dns").resolve()

if CBOR4DNS_PATH not in sys.path:
    sys.path.append(str(CBOR4DNS_PATH))
import cbor4dns.encode
import cbor4dns.decode


def decode_cbor_query(cbor):
    with io.BytesIO(cbor) as cbor_file:
        decoder = cbor4dns.decode.Decoder(cbor_file)
        return decoder.decode(cbor4dns.decode.MsgType.QUERY)


def decode_cbor_response(cbor, query_msg=None, packed=False):
    with io.BytesIO(cbor) as cbor_file:
        decoder = cbor4dns.decode.Decoder(cbor_file)
        return decoder.decode(cbor4dns.decode.MsgType.RESPONSE, query_msg, packed)


def encode_cbor(msg, query_msg=None, packed=False):
    with io.BytesIO() as cbor_file:
        encoder = cbor4dns.encode.Encoder(cbor_file, packed)
        encoder.encode(msg, query_msg)
        return cbor_file.getvalue()


class DoHLookupHandler(tornado.web.RequestHandler):
    def initialize(self, db_con):
        self._db_con = db_con

    async def post(self):
        resp_start = time.time()
        msgs = {}
        if self.request.headers.get("Content-Type") == "application/dns+cbor":
            cbor = True
            def decode_cbor():
                msgs["query"] = decode_cbor_query(self.request.body)
            decode_time = timeit.timeit(decode_cbor, number=1)
        else:
            cbor = False
            def decode_dns():
                msgs["query"] = dns.message.from_wire(self.request.body)
            decode_time = timeit.timeit(decode_dns, number=1)
        query = msgs["query"]
        question = query.question[0]
        name = question.name.to_text(omit_final_dot=True)
        qtype = question.rdtype
        cur = self._db_con.execute(
            """
            SELECT resp
            FROM dns_responses
            WHERE name = ? AND type = ?;
            """,
            (name, qtype),
        )
        res = cur.fetchone()
        if res and res[0]:
            resp = dns.message.from_text(res[0])
        else:
            resp = dns.message.make_response(query)

        if self.request.headers.get("Accept") == "application/dns+cbor":
            def encode_cbor_response():
                msgs["resp"] = encode_cbor(resp, self.request.body)
            self.set_header("Content-Type", "application/dns+cbor")
            encode_time = timeit.timeit(encode_cbor_response, number=1)
        elif self.request.headers.get("Accept") == "application/dns+cbor;packed=1":
            def encode_cbor_packed_response():
                msgs["resp"] = encode_cbor(resp, self.request.body, packed=True)
            self.set_header("Content-Type", "application/dns+cbor;packed=1")
            encode_time = timeit.timeit(encode_cbor_packed_response, number=1)
        else:
            def encode_dns_response():
                msgs["resp"] = resp.to_wire()
            self.set_header("Content-Type", "application/dns-message")
            encode_time = timeit.timeit(encode_dns_response, number=1)
        write_start = time.time()
        self.write(msgs["resp"])
        print(
            "doh-endpoint",
            name,
            qtype,
            resp_start,
            "",
            decode_time,
            encode_time,
            write_start,
            time.time() - resp_start,
            sep="\t",
        )


async def doh_query(
    q: dns.message.Message,
    where: str,
    timeout: Optional[float] = None,
    port: int = 443,
    source: Optional[str] = None,
    source_port: int = 0,  # pylint: disable=W0613
    one_rr_per_rrset: bool = False,
    ignore_trailing: bool = False,
    client: Optional["httpx.AsyncClient"] = None,
    path: str = "/dns-query",
    post: bool = True,
    verify: Union[bool, str] = True,
    bootstrap_address: Optional[str] = None,
    resolver: Optional["dns.asyncresolver.Resolver"] = None,
    family: Optional[int] = socket.AF_UNSPEC,
    cbor: bool = False,
    packed: bool = False,
) -> dns.message.Message:
    """Return the response obtained after sending a query via DNS-over-HTTPS.

    *client*, a ``httpx.AsyncClient``.  If provided, the client to use for
    the query.

    Unlike the other dnspython async functions, a backend cannot be provided
    in this function because httpx always auto-detects the async backend.

    See :py:func:`dns.query.https()` for the documentation of the other
    parameters, exceptions, and return type of this method.

    This was copied and adopted for application/dns+cbor (marked with CBOR: ...) from
    https://github.com/rthalley/dnspython/blob/v2.6.1/dns/asyncquery.py#L503-L718
    """

    if not have_doh:
        raise NoDOH  # pragma: no cover
    if client and not isinstance(client, httpx.AsyncClient):
        raise ValueError("session parameter must be an httpx.AsyncClient")

    # CBOR: Adopt for application/dns+cbor
    if cbor:
        wire = encode_cbor(q)
    else:
        wire = q.to_wire()
    try:
        af = dns.inet.af_for_address(where)
    except ValueError:
        af = None
    transport = None
    # CBOR: Adopt for application/dns+cbor
    if cbor:
        if packed:
            headers = {"accept": "application/dns+cbor;packed=1"}
        else:
            headers = {"accept": "application/dns+cbor"}
    else:
        headers = {"accept": "application/dns-message"}
    if af is not None and dns.inet.is_address(where):
        if af == socket.AF_INET:
            url = "https://{}:{}{}".format(where, port, path)
        elif af == socket.AF_INET6:
            url = "https://[{}]:{}{}".format(where, port, path)
    else:
        url = where

    backend = dns.asyncbackend.get_default_backend()

    if source is None:
        local_address = None
        local_port = 0
    else:
        local_address = source
        local_port = source_port
    transport = backend.get_transport_class()(
        local_address=local_address,
        http1=True,
        http2=True,
        verify=verify,
        local_port=local_port,
        bootstrap_address=bootstrap_address,
        resolver=resolver,
        family=family,
    )

    if client:
        cm: contextlib.AbstractAsyncContextManager = NullContext(client)
    else:
        cm = httpx.AsyncClient(
            http1=True, http2=True, verify=verify, transport=transport
        )

    async with cm as the_client:
        # see https://tools.ietf.org/html/rfc8484#section-4.1.1 for DoH
        # GET and POST examples
        if post:
            headers.update(
                {
                    # CBOR: Adoption for application/dns+cbor
                    "content-type": (
                        "application/dns+cbor" if cbor else "application/dns-message"
                    ),
                    "content-length": str(len(wire)),
                }
            )
            response = await backend.wait_for(
                the_client.post(url, headers=headers, content=wire), timeout
            )
        else:
            wire = base64.urlsafe_b64encode(wire).rstrip(b"=")
            twire = wire.decode()  # httpx does a repr() if we give it bytes
            response = await backend.wait_for(
                the_client.get(url, headers=headers, params={"dns": twire}), timeout
            )

    # see https://tools.ietf.org/html/rfc8484#section-4.2.1 for info about DoH
    # status codes
    if response.status_code < 200 or response.status_code > 299:
        raise ValueError(
            "{} responded with status code {}"
            "\nResponse body: {!r}".format(
                where, response.status_code, response.content
            )
        )
    # CBOR: Adoption for application/dns+cbor
    if response.headers["content-type"].startswith("application/dns+cbor"):
        assert post
        r = decode_cbor_response(
            response.content,
            wire,
            response.headers["content-type"] == "application/dns+cbor;packed=1"
        )
    else:
        r = dns.message.from_wire(
            response.content,
            keyring=q.keyring,
            request_mac=q.request_mac,
            one_rr_per_rrset=one_rr_per_rrset,
            ignore_trailing=ignore_trailing,
        )
    r.time = response.elapsed.total_seconds()
    if not q.is_response(r):
        raise BadResponse
    return r


class DoHDelegateHandler(tornado.web.RequestHandler):
    def initialize(self, upstream_doh, encode_cbor=False, accept_packed=False):
        self.upstream_doh = upstream_doh
        self.encode_cbor = encode_cbor
        self.accept_packed = accept_packed

    async def post(self):
        resp_start = time.time()
        dns_query = dns.message.from_wire(self.request.body)
        question = dns_query.question[0]
        name = question.name.to_text(omit_final_dot=True)
        qtype = question.rdtype
        qry_start = time.time()
        dns_resp = await doh_query(
            dns_query,
            self.upstream_doh,
            verify=False,
            cbor=self.encode_cbor,
            packed=self.accept_packed,
        )
        qry_stop = time.time()
        self.set_header("Content-Type", "application/dns-message")
        write_start = time.time()
        self.write(dns_resp.to_wire())
        print(
            "delegate",
            name,
            qtype,
            resp_start,
            qry_stop - qry_start,
            "",
            "",
            write_start,
            time.time() - resp_start,
            sep="\t",
        )


class TestHandler(tornado.web.RequestHandler):
    async def get(self):
        self.set_header("Content-Type", "application/json")
        self.write("{}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-g",
        "--gzip-responses",
        action="store_true",
        help="Compress responses with gzip",
    )
    parser.add_argument(
        "-c",
        "--encode-cbor",
        action="store_true",
        help="Encode with application/dns+cbor",
    )
    parser.add_argument(
        "-P",
        "--encode-packed",
        action="store_true",
        help="Encode with application/dns+cbor;packed. Ignored when --encode-cbor is not set",
    )
    parser.add_argument("-p", "--port")
    parser.add_argument("database")
    args = parser.parse_args()

    if not hasattr(cbor4dns.encode, "RefIdx"):
        raise RuntimeError(
            "Wrong cbor4dns branch checked out, please provide "
            "name component referencing"
        )
    if args.gzip_responses:
        # tornado.web.GZipContentEncoding.MIN_LENGTH = 0
        # tornado.web.GZipContentEncoding.GZIP_LEVEL = 9
        tornado.web.GZipContentEncoding.CONTENT_TYPES |= set(
            (
                "application/dns+cbor",
                "application/dns-message",
            )
        )
    with sqlite3.connect(args.database) as con:
        app = tornado.web.Application(
            [
                (
                    r"/dns-query",
                    DoHLookupHandler,
                    dict(db_con=con),
                ),
                (
                    r"/delegate",
                    DoHDelegateHandler,
                    dict(
                        upstream_doh=f"https://127.0.0.1:{args.port}/dns-query",
                        encode_cbor=args.encode_cbor,
                        accept_packed=args.encode_packed,
                    ),
                ),
                (r"/style/favicon/manifest.json", TestHandler),
            ],
            compress_response=args.gzip_responses,
        )
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(SCRIPT_PATH / "domain.crt", SCRIPT_PATH / "domain.key")
        doh_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
        doh_server.listen(args.port)
        print(
            "req_handler",
            "name",
            "qtype",
            "req_recv",
            "doh_query_time",
            "query_decode_time",
            "response_encode_time",
            "write_time",
            "handler_time",
            sep="\t",
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
