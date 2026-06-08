#! /usr/bin/env python3
#
# Copyright (C) 2024 Martine S. Lenders <martine.lenders@tu-dresden.de>
#
# Distributed under terms of the MIT license.


import argparse
import collections
import json
import re
import sqlite3
import sys
import traceback
import warnings

import bs4
import json5
import requests
import requests.exceptions
import tinycss2
import urllib3.exceptions


KEYS = {}
SPECIAL_VALUES = {}


def update_stats(key, value=None):
    if key in KEYS:
        KEYS[key] += 1
    else:
        KEYS[key] = 1
    if value is not None:
        if key in SPECIAL_VALUES:
            if value in SPECIAL_VALUES[key]:
                SPECIAL_VALUES[key][value] += 1
            else:
                SPECIAL_VALUES[key][value] = 1
        else:
            try:
                SPECIAL_VALUES[key] = {value: 1}
            except TypeError:
                print(key, value)


def add_navigable_string(name, content):
    if re.match(r"^\s*$", content) and name not in [
        "!-- COMMENT",
        "!CDATA",
        "!DOCTYPE",
    ]:
        # content only white spaces so effectively empty
        return {}
    if name != "str":
        update_stats("NAME", name)
        update_stats("CONTENT")
    return {"NAME": name, "CONTENT": [content]}


def xml_child_to_dict(elem):
    tag = {}
    if isinstance(elem, bs4.Declaration):
        tag = add_navigable_string("?xml", elem.string)
    elif isinstance(elem, bs4.ProcessingInstruction):
        tag = add_navigable_string("?PI", elem.string)
    elif isinstance(elem, bs4.Doctype):
        tag = add_navigable_string("!DOCTYPE", elem.string)
    elif isinstance(elem, bs4.CData):
        tag = add_navigable_string("!CDATA", elem.string)
    elif isinstance(elem, bs4.Stylesheet):
        tag = add_navigable_string("<STYLESHEET", elem.string)
    elif isinstance(elem, bs4.Script):
        tag = add_navigable_string("<SCRIPT", elem.string)
    elif isinstance(elem, bs4.Comment):
        tag = add_navigable_string("!-- COMMENT", elem.string)
    elif isinstance(elem, bs4.TemplateString):
        tag = add_navigable_string("<TEMPLATE", elem.string)
    elif isinstance(elem, bs4.NavigableString):
        if type(elem) != bs4.NavigableString:
            raise ValueError(f"Unknown element, {type(elem)}, {elem}")
        tag = add_navigable_string("str", elem.string)
    elif isinstance(elem, bs4.Tag):
        children = xml_children_to_dicts(elem)

        tag = {
            "NAME": elem.name.lower(),
        }
        update_stats("NAME", elem.name.lower())
        if children:
            update_stats("CONTENT")
            tag["CONTENT"] = children
        for key in elem.attrs:
            lower_key = key.lower()
            if lower_key in ["class", "id", "style", "accesskey"]:
                continue
            if lower_key in ["rel", "accept-charset"]:
                for value in elem.attrs[key]:
                    update_stats(lower_key, value)
            else:
                update_stats(lower_key, elem.attrs[key])
            tag[lower_key] = elem.attrs[key]
    else:
        raise ValueError(f"Unknown element, {type(elem)}, {elem}")
    return tag


def xml_children_to_dicts(parent):
    res = []
    for elem in parent.childGenerator():
        tag = xml_child_to_dict(elem)
        if tag:
            res.append(tag)
        elif type(elem) not in [bs4.Script, bs4.Stylesheet, bs4.TemplateString]:
            assert (
                type(elem) == bs4.NavigableString
            ), f"OK to skip? {type(elem)}, {repr(elem)}, {elem.parent}"
    return res


class CSSTokenList:
    def __init__(self, init=None):
        if init is None:
            self._list = []
        else:
            self._list = init

    def __repr__(self):
        return f"<CSSTokenList {self._list}>"

    def append(self, element):
        self._list.append(element)

    @property
    def list(self):
        return self._list


def append_css_token(lst, token):
    if isinstance(lst, list):
        # append to list of list for duplicate ident
        lst[-1].append(token)
    else:
        lst.append(token)


def construct_css_rule_content(rule_content, token, last_ident):
    if token.type == "{} block":
        raise NotImplementedError("Nested CSS not supported yet")
    if token.type == "ident":
        if last_ident is None:
            last_ident = token.value.strip()
        else:
            assert last_ident in rule_content
            append_css_token(rule_content[last_ident], token)
    elif token.type == "literal":
        if token.value == ":":
            if last_ident in rule_content:
                # duplicate ident, make list of lists and start appending
                if isinstance(rule_content[last_ident], list):
                    rule_content[last_ident].append(CSSTokenList())
                else:
                    rule_content[last_ident] = [
                        rule_content[last_ident],
                        CSSTokenList(),
                    ]
            else:
                # else content is just a list of tokens
                rule_content[last_ident] = CSSTokenList()
        elif token.value == ";":
            if last_ident is not None:
                update_stats(last_ident.lower())
                assert last_ident in rule_content
            last_ident = None
        elif last_ident is not None:
            append_css_token(rule_content[last_ident], token)
    elif last_ident in rule_content:
        append_css_token(rule_content[last_ident], token)
    else:
        assert token.type in ["whitespace", "comment"], token.serialize()
    return last_ident


def css_to_dict(css):
    res = collections.OrderedDict()
    for rule in css:
        if rule.type == "at-rule":
            key = f"@{rule.at_keyword} {tinycss2.serialize(rule.prelude).strip()}"
            if rule.content is None:  # semicolon
                res[key] = rule.content
            else:
                res[key] = {}
                last_tokens = []
                for content_token in rule.content:
                    if content_token.type == "{} block":
                        content_key = tinycss2.serialize(last_tokens).strip()
                        res[key][content_key] = {}
                        last_ident = None
                        for token in content_token.content:
                            last_ident = construct_css_rule_content(
                                res[key][content_key], token, last_ident
                            )
                        last_tokens = []
                    else:
                        last_tokens.append(content_token)
        # TODO https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_nesting/Using_CSS_nesting
        elif rule.type == "qualified-rule":
            key = tinycss2.serialize(rule.prelude).strip()
            res[key] = {}
            last_ident = None
            for token in rule.content:
                last_ident = construct_css_rule_content(res[key], token, last_ident)
        elif rule.type in ["comment", "whitespace"]:
            pass
        elif rule.type == "error":
            raise ValueError("Unable to parse as CSS")
        else:
            print("unable to convert", rule, rule.type, tinycss2.serialize([rule]))
    return res


def default_json_encoder(value):
    if isinstance(value, CSSTokenList):
        if len(value.list) == 1:
            if value.list[0].type == "number":
                try:
                    if int(value.list[0].value) == value.list[0].value:
                        return int(value.list[0].value)
                except OverflowError:
                    pass
            if value.list[0].type == "ident" and value.list[0].value == "none":
                return None
        return tinycss2.serialize(value.list).strip()
    else:
        raise ValueError(f"Can not encode {value} (type {type(value)}")


def write_error_to_db(database, url, lib):
    trace = traceback.format_exc()
    for _ in range(100):
        try:
            con = sqlite3.connect(database)
            con.execute(
                "INSERT INTO errors (url, lib, error) VALUES (?, ?, ?)",
                (url, lib, trace),
            )
            con.commit()
            con.close()
            break
        except sqlite3.OperationalError as exc:
            if exc.sqlite_errorcode != 5:
                raise
            time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("url")
    args = parser.parse_args()

    warnings.filterwarnings(
        "ignore", category=urllib3.exceptions.InsecureRequestWarning
    )
    warnings.filterwarnings("ignore", category=bs4.MarkupResemblesLocatorWarning)
    try:
        resp = requests.get(args.url, verify=False, timeout=120)
    except (
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ConnectionError,
        requests.exceptions.ContentDecodingError,
        requests.exceptions.InvalidSchema,
        requests.exceptions.InvalidURL,
        requests.exceptions.SSLError,
        requests.exceptions.Timeout,
        requests.exceptions.TooManyRedirects,
        urllib3.exceptions.IncompleteRead,
        urllib3.exceptions.ProtocolError,
        urllib3.exceptions.ReadTimeoutError,
        TimeoutError,
    ):
        write_error_to_db(args.database, args.url, "requests")
        return
    res = None
    typ = None
    resp_len = len(resp.content)
    try:
        res = json5.loads(resp.content)
        typ = "json"
    except (ValueError, RecursionError):
        try:
            res = resp.json()
            typ = "json"
        except json.JSONDecodeError:
            pass
    if typ is None:
            soup = bs4.BeautifulSoup(resp.content, "xml")
            try:
                res = xml_children_to_dicts(soup)
                if res:
                    typ = "html"
            except (AssertionError, RecursionError):
                write_error_to_db(args.database, args.url, "bs4")
                return
    if typ is None:
        try:
            css, _ = tinycss2.parse_stylesheet_bytes(
                resp.content,
                skip_comments=True,
                skip_whitespace=True
            )
            if css:
                res = css_to_dict(css)
                typ = "css"
        except (
            TypeError,
            KeyError,
            NotImplementedError,
            ValueError,
            AssertionError,
            RecursionError,
        ):
            write_error_to_db(args.database, args.url, "css")
            return
    if res:
        for _ in range(100):
            try:
                con = sqlite3.connect(args.database)
                cursor = con.execute(
                    "INSERT INTO objects(url, type, orig_len, object) "
                    "VALUES (?, ?, ?, ?);",
                    (
                        args.url,
                        typ,
                        resp_len,
                        json.dumps(
                            res,
                            separators=(",", ":"),
                            default=default_json_encoder,
                        ).encode(),
                    ),
                )
                obj_id = cursor.lastrowid
                for key in KEYS:
                    cursor = con.execute(
                        "INSERT INTO keys(obj_id, key, count) VALUES (?, ?, ?);",
                        (obj_id, key, KEYS[key]),
                    )
                    key_id = cursor.lastrowid
                    if key in SPECIAL_VALUES:
                        cursor = con.executemany(
                            """
                            INSERT INTO special_values(key_id, value, count)
                                VALUES (?, ?, ?);
                            """,
                            [
                                (key_id, value, SPECIAL_VALUES[key][value])
                                for value in SPECIAL_VALUES[key]
                            ],
                        )
                con.commit()
                con.close()
                break
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode != 5:
                    raise
                time.sleep(0.2)


if __name__ == "__main__":
    main()
