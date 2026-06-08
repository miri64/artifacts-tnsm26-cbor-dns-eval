#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import asyncio
import base64
import collections
import json
import pathlib
import re
import sqlite3
import sys
import time
import urllib.parse
import timeit
import traceback

import cbor2
import dns.message
import dns.query
import tornado
import ssl


SCRIPT_PATH = pathlib.Path(__file__).parent


def encode_html(obj):
    res = ""
    for elem in obj:
        assert "NAME" in elem, f'"NAME" not in {elem} of {obj}'
        if elem["NAME"] == "?xml":
            res += f"<?xml {elem['CONTENT'][0]}>"
        elif elem["NAME"] == "?PI":
            res += f"<?{elem['CONTENT'][0]}>"
        elif elem["NAME"] == "!DOCTYPE":
            res += f"<!DOCTYPE {elem['CONTENT'][0]}>"
        elif elem["NAME"] == "!CDATA":
            res += f"<![CDATA[{elem['CONTENT'][0]}]]>"
        elif elem["NAME"] == "<STYLESHEET":
            res += f"{elem['CONTENT'][0]}"
        elif elem["NAME"] == "<SCRIPT":
            res += f"{elem['CONTENT'][0]}"
        elif elem["NAME"] == "!-- COMMENT":
            res += f"<!--{elem['CONTENT'][0]}-->"
        elif elem["NAME"] == "TEMPLATE":
            res += f"{elem['CONTENT'][0]}"
        elif elem["NAME"] == "str":
            res += f"{elem['CONTENT'][0]}"
        else:
            res += f"<{elem['NAME']}"
            for key in elem:
                if key in ["NAME", "CONTENT"]:
                    continue
                res += f' {key}="{elem[key]}"'
            if "CONTENT" in elem:
                res += ">"
                res += encode_html(elem["CONTENT"])
                res += f"</{elem['NAME']}>"
            else:
                res += "/>"
    return res


def encode_css_rule(obj):
    res = "{"
    if obj is not None:
        for key, value in obj.items():
            if isinstance(value, list):
                for val in value:
                    res += f"{key}:{val};"
            else:
                res += f"{key}:{value};"
    res += "}"
    return res


def encode_css(obj):
    res = ""
    for key, value in obj.items():
        if key.startswith("@"):
            # is object a dictionary of rules?
            if obj[key] and isinstance(obj[key][[k for k in obj[key]][0]], dict):
                # recurse deeper
                if isinstance(value, list):
                    for val in value:
                        res += f"{key}" "{" f"{encode_css(val)}" "}"
                else:
                    res += f"{key}" "{" f"{encode_css(value)}" "}"
            else:
                # interpret as directly as rule
                if isinstance(value, list):
                    for val in value:
                        res += f"{key}" "{" f"{encode_css_rule(val)}" "}"
                else:
                    res += f"{key}{encode_css_rule(value)}"
        else:
            if isinstance(value, list):
                for val in value:
                    res += f"{key}" "{" f"{encode_css_rule(val)}" "}"
            else:
                res += f"{key}{encode_css_rule(value)}"
    return res


def encode_cbor_html_obj(obj, html_key_idx, html_name_idx):
    res = []
    for elem in obj:
        assert isinstance(elem, (str, dict))
        if isinstance(elem, str):
            res.append(elem)
        elif elem.get("NAME") == "str":
            res.append(elem["CONTENT"][0])
        else:
            item = {}
            for key, val in elem.items():
                if key == "NAME":
                    item[html_key_idx.get(key, key)] = html_name_idx.get(val, val)
                elif key == "CONTENT":
                    item[html_key_idx.get(key, key)] = encode_cbor_html_obj(
                        val,
                        html_key_idx,
                        html_name_idx,
                    )
                else:
                    item[html_key_idx.get(key, key)] = val
            res.append(item)
    return res


def encode_cbor_html(obj, html_key_idx, html_name_idx):
    return cbor2.dumps(encode_cbor_html_obj(obj, html_key_idx, html_name_idx))


def encode_cbor_css_rule(obj, css_ident_idx):
    if obj is not None:
        res = {}
        for key, value in obj.items():
            res[css_ident_idx.get(key, key)] = value
        return res
    else:
        return None


def encode_cbor_css_obj(obj, css_ident_idx):
    res = {}
    for key in obj:
        if key.startswith("@"):
            # is object a dictionary of rules?
            if obj[key] and isinstance(obj[key][[k for k in obj[key]][0]], dict):
                # recurse deeper
                res[key] = encode_cbor_css_obj(obj[key], css_ident_idx)
            else:
                # interpret as directly as rule
                res[key] = encode_cbor_css_rule(obj[key], css_ident_idx)
        else:
            res[key] = encode_cbor_css_rule(obj[key], css_ident_idx)
    return res


def encode_cbor_css(obj, css_ident_idx):
    return cbor2.dumps(encode_cbor_css_obj(obj, css_ident_idx))


class QueryHandler(tornado.web.RequestHandler):
    def initialize(self, db_con, encode_cbor=False, html_key_idx=None, html_name_idx=None, css_ident_idx=None):
        self._con = db_con
        self._encode_cbor = encode_cbor
        self.handled_urls = {}
        self.html_key_idx = html_key_idx or {}
        self.html_name_idx = html_name_idx or {}
        self.css_ident_idx = css_ident_idx or {}

    async def get(self, path):
        resp_start = time.time()
        exp_count = int(self.get_query_argument("exp_count", default="1"))
        orig_query = re.sub(r"&?exp_count=\d+", "", self.request.query)
        url_parts = urllib.parse.ParseResult(
            scheme=self.request.protocol,
            netloc=self.request.headers["Host"],
            path=path,
            params="",
            query=orig_query,
            fragment="",  # We have no URLs with "#" in our data set so this is fine
        )
        url = urllib.parse.urlunparse(url_parts)
        handled_ids = [
            key
            for key, value in self.handled_urls.get(url, {}).items()
            if value > exp_count
        ]
        cursor = self._con.execute(
            "SELECT id, type, object FROM objects WHERE url = ? OR url = ?"
            f'{"".join(f" AND id != {id:d}" for id in handled_ids)}',
            (url, f"{url}?"),
        )
        id, typ, obj_b = cursor.fetchone() or (None, None, None)
        if typ is None:
            print(
                f"Decoding error on {url} (handled_ids={handled_ids})",
                file=sys.stderr
            )
            self.set_status(404)
            return
        if url in self.handled_urls:
            self.handled_urls[url][id] = exp_count
        else:
            self.handled_urls[url] = {id: exp_count}
        obj = json.loads(obj_b, object_pairs_hook=collections.OrderedDict)
        res = {}
        if self._encode_cbor:
            if typ == "json":
                self.set_header("Content-Type", "application/cbor")

                def json_cbor_enc():
                    res["res"] = cbor2.dumps(obj)

                enc_time = timeit.timeit(json_cbor_enc, number=1)
                write_start = time.time()
                self.write(res["res"])
            elif typ == "css":
                self.set_header("Content-Type", "application/cbor;css=1")

                def cbor_css_enc():
                    res["res"] = encode_cbor_css(obj, self.css_ident_idx)

                enc_time = timeit.timeit(cbor_css_enc, number=1)
                write_start = time.time()
                self.write(res["res"])
            elif typ == "html":
                self.set_header("Content-Type", "application/cbor;html=1")

                def html_cbor_enc():
                    res["res"] = encode_cbor_html(
                        obj,
                        self.html_key_idx,
                        self.html_name_idx
                    )

                enc_time = timeit.timeit(html_cbor_enc, number=1)
                write_start = time.time()
                self.write(res["res"])
                pass
        else:
            if typ == "json":
                self.set_header("Content-Type", "application/json")

                def json_enc():
                    res["res"] = json.dumps(obj, separators=(",", ":"))

                enc_time = timeit.timeit(json_enc, number=1)
                write_start = time.time()
                self.write(res["res"])
            elif typ == "css":
                self.set_header("Content-Type", "text/css")

                def css_enc():
                    res["res"] = encode_css(obj)

                enc_time = timeit.timeit(css_enc, number=1)
                write_start = time.time()
                self.write(res["res"])
            elif typ == "html":
                self.set_header("Content-Type", "text/html")

                def html_enc():
                    res["res"] = encode_html(obj)

                enc_time = timeit.timeit(html_enc, number=1)
                write_start = time.time()
                self.write(res["res"])
                pass
        print(
            id,
            url,
            self._encode_cbor,
            self.settings.get("compress_response"),
            typ,
            len(res["res"]) if "res" in res else -1,
            exp_count,
            resp_start,
            enc_time,
            write_start,
            time.time() - resp_start,
            sep="\t",
        )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--gzip-responses", action="store_true")
    parser.add_argument("-c", "--cbor", action="store_true")
    parser.add_argument("-p", "--http-port", type=int, default=8888)
    parser.add_argument("-s", "--https-port", type=int, default=8433)
    parser.add_argument(
        "-hk", "--html-key-idx", type=pathlib.Path,
        default=SCRIPT_PATH / "output_datasets" / "html-key-idx.json"
    )
    parser.add_argument(
        "-hn", "--html-name-idx", type=pathlib.Path,
        default=SCRIPT_PATH / "output_datasets" / "html-name-idx.json"
    )
    parser.add_argument(
        "-ci", "--css-ident-idx", type=pathlib.Path,
        default=SCRIPT_PATH / "output_datasets" / "css-ident-idx.json"
    )
    parser.add_argument("database")
    args = parser.parse_args()

    if args.gzip_responses:
        # tornado.web.GZipContentEncoding.MIN_LENGTH = 0
        # tornado.web.GZipContentEncoding.GZIP_LEVEL = 9
        tornado.web.GZipContentEncoding.CONTENT_TYPES |= set(
            (
                "application/cbor",
                "application/cbor;css=1",
                "application/cbor;html=1",
            )
        )
    with open(args.html_key_idx) as jf:
        html_key_idx = json.load(jf)
    with open(args.html_name_idx) as jf:
        html_name_idx = json.load(jf)
    with open(args.css_ident_idx) as jf:
        css_ident_idx = json.load(jf)
    with sqlite3.connect(args.database) as con:
        app = tornado.web.Application(
            [
                (r"^(/.*)$", QueryHandler, dict(
                    db_con=con, 
                    encode_cbor=args.cbor,
                    html_key_idx=html_key_idx,
                    html_name_idx=html_name_idx,
                    css_ident_idx=css_ident_idx,
                )),
            ],
            compress_response=args.gzip_responses,
        )
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(SCRIPT_PATH / "domain.crt", SCRIPT_PATH / "domain.key")
        https_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
        https_server.listen(args.https_port)
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.listen(args.http_port)
        print(
            "obj_id", "url", "cbor", "gzip", "type", "resp_len", "exp_count", "req_recv", "enc_time", "write_start", "handler_time", sep="\t"
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
