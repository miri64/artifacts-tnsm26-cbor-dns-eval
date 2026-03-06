#! /usr/bin/env python3
#
# Copyright (C) 2024 Martine S. Lenders <martine.lenders@tu-dresden.de>
#
# Distributed under terms of the MIT license.

## Copied on 2024-12-16 from mobi6, 06_discussion.


import argparse
import collections
import json
import pathlib
import re
import sqlite3
import sys
import traceback
import warnings

import bs4
import cbor2
import json5
import tinycss2


SCRIPT_PATH = pathlib.Path(__file__).parent

KEYS = {}
SPECIAL_VALUES = {}


def update_stats(typ, key, value=None):
    if typ not in KEYS:
        KEYS[typ] = {}
    if key in KEYS[typ]:
        KEYS[typ][key] += 1
    else:
        KEYS[typ][key] = 1
    if value is not None:
        if typ not in SPECIAL_VALUES:
            SPECIAL_VALUES[typ] = {}
        if key in SPECIAL_VALUES[typ]:
            if value in SPECIAL_VALUES[typ][key]:
                SPECIAL_VALUES[typ][key][value] += 1
            else:
                SPECIAL_VALUES[typ][key][value] = 1
        else:
            try:
                SPECIAL_VALUES[typ][key] = {value: 1}
            except TypeError:
                print(typ, key, value)


def add_navigable_string(name, content):
    if re.match(r"^\s*$", content) and name not in [
        "!-- COMMENT",
        "!CDATA",
        "!DOCTYPE",
    ]:
        # content only white spaces so effectively empty
        return {}
    if name != "str":
        update_stats("html", "NAME", name)
        update_stats("html", "CONTENT")
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
        css = tinycss2.parse_stylesheet(
            elem.string,
            skip_comments=True,
            skip_whitespace=True
        )
        assert css
        # add to CSS ident index
        css_to_dict(css)
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
        update_stats("html", "NAME", elem.name.lower())
        if children:
            update_stats("html", "CONTENT")
            tag["CONTENT"] = children
        for key in elem.attrs:
            lower_key = key.lower()
            if lower_key in ["class", "id", "style", "accesskey"]:
                continue
            if lower_key in ["rel", "accept-charset"]:
                for value in elem.attrs[key]:
                    update_stats("html", lower_key, value)
            else:
                update_stats("html", lower_key, elem.attrs[key])
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
        if last_ident == ":host":
            block = css_to_dict(tinycss2.parse_blocks_contents(token.content,
                        skip_comments=True,
                        skip_whitespace=True))
            rule_content[last_ident] = block
            return None
        else:
            raise NotImplementedError(f"Nested CSS not supported yet")
    if token.type == "ident":
        if last_ident == ":":
            last_ident += token.value.strip()
        elif last_ident is None:
            last_ident = token.value.strip()
        else:
            assert last_ident in rule_content
            append_css_token(rule_content[last_ident], token)
    elif token.type == "literal":
        if token.value == ":":
            if last_ident is None:
                return ":"
            elif last_ident in rule_content:
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
                update_stats("css", last_ident.lower())
                assert last_ident in rule_content
            last_ident = None
        elif last_ident is not None:
            append_css_token(rule_content[last_ident], token)
    elif last_ident in rule_content:
        append_css_token(rule_content[last_ident], token)
    else:
        assert token.type in ["whitespace", "comment"]
    return last_ident


def css_to_dict(css):
    res = collections.OrderedDict()
    for rule in css:
        if rule.type == "at-rule":
            key = f"@{rule.at_keyword} {tinycss2.serialize(rule.prelude).strip()}"
            if rule.content is None:  # semicolon
                res[key] = rule.content
            else:
                block = css_to_dict(tinycss2.parse_blocks_contents(rule.content,
                        skip_comments=True,
                        skip_whitespace=True))
                if key not in res:
                    res[key] = block
                else:
                    if isinstance(res[key], list):
                        res[key].append(block)
                    else:
                        if set(res[key].keys()) & set(block.keys()):
                            res[key] = [res[key], block]
                        else:
                            res[key].update(block)
        elif rule.type == "qualified-rule":
            key = tinycss2.serialize(rule.prelude).strip()
            if key in res:
                block = collections.OrderedDict()
                if isinstance(res[key], list):
                    res[key].append(block)
                else:
                    res[key] = [res[key], block]
            else:
                res[key] = collections.OrderedDict()
                block = res[key]
            last_ident = None
            for token in rule.content:
                last_ident = construct_css_rule_content(block, token, last_ident)
        elif rule.type == "declaration":
            update_stats("css", rule.lower_name)
            res[rule.lower_name] = tinycss2.serialize(rule.value)
        elif rule.type in ["comment", "whitespace"]:
            pass
        elif rule.type == "error":
            raise ValueError("Unable to parse as CSS")
        else:
           print("unable to convert", rule, rule.type, tinycss2.serialize([rule]))
    return res


def write_error(file, lib):
    trace = traceback.format_exc()
    print(f"==== {file}:{lib} ====\n{trace}", file=sys.stderr)
    

def encode_cbor_html_obj(obj, html_key_idx, html_name_idx, css_ident_idx):
    res = []
    for elem in obj:
        assert isinstance(elem, (str, dict))
        if isinstance(elem, str):
            res.append(elem)
        elif elem.get("NAME") == "str":
            res.append(elem["CONTENT"][0])
        else:
            if elem.get("NAME") == "script":
                if elem.get("type") in ["application/json", "application/ld+json"]:
                    if elem["type"] == "application/ld+json":
                        # note: there is actually https://json-ld.github.io/cbor-ld-spec/
                        # but we just convert straight for now
                        elem["type"] = "application/ld+cbor"
                    else:
                        # note: there is actually https://json-ld.github.io/cbor-ld-spec/
                        # but we just convert straight for now
                        elem["type"] = "application/cbor"
                    elem["CONTENT"] = cbor2.CBORTag(
                        24,
                        cbor2.dumps(json.loads(elem["CONTENT"][0]["CONTENT"][0]),
                                    canonical=True)
                    )
            if elem.get("NAME") == "style":
                if elem.get("type", "text/css") in ["text/css"]:
                    if "type" in elem and elem["type"] == "text/css":
                        elem["type"] = "application/css+cbor"

                    css = tinycss2.parse_stylesheet(
                        elem["CONTENT"][0]["CONTENT"][0],
                        skip_comments=True,
                        skip_whitespace=True
                    )
                    assert css
                    css_cbor = css_to_dict(css)
                    elem["CONTENT"] = cbor2.CBORTag(
                        24,
                        encode_cbor_css(css_cbor, css_ident_idx)
                    )
            item = {}
            for key, val in elem.items():
                if key == "NAME":
                    item[html_key_idx.get(key, key)] = html_name_idx.get(val, val)
                elif key == "CONTENT":
                    if isinstance(val, cbor2.CBORTag):
                        # already encoded above
                        item[html_key_idx.get(key, key)] = val
                    else:
                        item[html_key_idx.get(key, key)] = encode_cbor_html_obj(
                            val,
                            html_key_idx,
                            html_name_idx,
                            css_ident_idx,
                        )
                else:
                    item[html_key_idx.get(key, key)] = val
            res.append(item)
    return res


def encode_cbor_html(obj, html_key_idx, html_name_idx, css_ident_idx):
    return cbor2.dumps(encode_cbor_html_obj(obj, html_key_idx, html_name_idx,
                                            css_ident_idx), canonical=True)


def encode_cbor_css_rule(obj, css_ident_idx):
    res = {}
    if isinstance(obj, list):
        intersects = False
        tmp = collections.OrderedDict()
        for item in obj:
            if set(tmp.keys()) & set(item.keys()):
                tmp = collections.OrderedDict()
                intersects = True
                break
            tmp.update(item)
        if intersects:
            res = []
            for item in obj:
                res.append(encode_cbor_css_rule(item, css_ident_idx))
            return res
        else:
            obj = tmp
    for key, value in obj.items():
        res[css_ident_idx.get(key, key)] = value
    return res


def encode_cbor_css_obj(obj, css_ident_idx):
    res = {}
    intersection = set()
    if isinstance(obj, list):
        tmp = collections.OrderedDict()
        for item in obj:
            intersection = set(tmp.keys()) & set(item.keys())
            if not intersection:
                tmp.update(item)
            else:
                for key in intersection:
                    if key in item:
                        if isinstance(tmp[key], list):
                            tmp[key].append(item[key])
                        else:
                            tmp[key] = [tmp[key], item[key]]
        obj = tmp
    for key in obj:
        if key.startswith("@"):
            if obj[key] is None:
                res[key] = None
            else:
                res[key] = encode_cbor_css_obj(obj[key], css_ident_idx)
        else:
            if isinstance(obj[key], dict):
                res[key] = encode_cbor_css_rule(obj[key], css_ident_idx)
            elif isinstance(obj[key], str) or isinstance(obj[key], CSSTokenList) or (
                isinstance(obj[key], list) and (
                    all(isinstance(i, (str, CSSTokenList)) for i in obj[key])
                )
            ):
                res[css_ident_idx.get(key, key)] = obj[key]
            else:
                res[key] = encode_cbor_css_obj(obj[key], css_ident_idx)
    return res


def default_cbor_encoder(encoder, value):
    if isinstance(value, CSSTokenList):
        if len(value.list) == 1:
            if value.list[0].type == "number":
                try:
                    if int(value.list[0].value) == value.list[0].value:
                        return encoder.encode(int(value.list[0].value))
                except OverflowError:
                    pass
            if value.list[0].type == "ident" and value.list[0].value == "none":
                encoder.encode(None)
        return encoder.encode(tinycss2.serialize(value.list).strip())
    else:
        raise ValueError(f"Can not encode {value} (type {type(value)}")


def encode_cbor_css(obj, css_ident_idx):
    return cbor2.dumps(
        encode_cbor_css_obj(obj, css_ident_idx),
        default=default_cbor_encoder,
        canonical=True
    )


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--collect-index", type=pathlib.Path, metavar="SQLITE_DATABASE", default=None)
    group.add_argument("--create-index", type=pathlib.Path, metavar="SQLITE_DATABASE", default=None)
    parser.add_argument(
        "-hk", "--html-key-idx", type=pathlib.Path,
        default=SCRIPT_PATH / "idxs" / "html-key-idx.json"
    )
    parser.add_argument(
        "-hn", "--html-name-idx", type=pathlib.Path,
        default=SCRIPT_PATH / "idxs" / "html-name-idx.json"
    )
    parser.add_argument(
        "-ci", "--css-ident-idx", type=pathlib.Path,
        default=SCRIPT_PATH / "idxs" / "css-ident-idx.json"
    )
    parser.add_argument("file", nargs="?", type=pathlib.Path, default=None)
    args = parser.parse_args()

    if args.create_index:
        with sqlite3.connect(args.create_index) as con:
            cursor = con.execute(
                """
                SELECT key, SUM(count) AS total_count 
                FROM keys
                WHERE type == "html"
                GROUP BY key
                ORDER BY total_count DESC;
                """
            )
            idx = 0
            res = {}
            for key, _ in cursor.fetchall():
                if (23 < idx < 0xff and len(key) == 1) or (0xff < idx < 0xffff and len(key) < 3):
                    # idx would increase size in CBOR compared to string
                    continue
                res[key] = idx
                idx += 1
            with open(args.html_key_idx, "wt") as jf:
                json.dump(res, jf, separators=(",", ":"))
            cursor = con.execute(
                """
                SELECT value, SUM(special_values.count) AS total_count 
                FROM special_values
                JOIN keys ON special_values.key_id = keys.id
                WHERE type == "html" AND key == "NAME" AND value != "str"
                GROUP BY value
                ORDER BY total_count DESC;
                """
            )
            idx = 0
            res = {}
            for key, _ in cursor.fetchall():
                if (23 < idx < 0xff and len(key) == 1) or (0xff < idx < 0xffff and len(key) < 3):
                    # idx would increase size in CBOR compared to string
                    continue
                res[key] = idx
                idx += 1
            with open(args.html_name_idx, "wt") as jf:
                json.dump(res, jf, separators=(",", ":"))
            cursor = con.execute("""
                SELECT key, SUM(count) AS total_count 
                FROM keys
                WHERE type == "css"
                GROUP BY key
                ORDER BY total_count DESC;
            """)
            idx = 0
            res = {}
            for key, _ in cursor.fetchall():
                if (23 < idx < 0xff and len(key) == 1) or (0xff < idx < 0xffff and len(key) < 3):
                    # idx would increase size in CBOR compared to string
                    continue
                res[key] = idx
                idx += 1
            with open(args.css_ident_idx, "wt") as jf:
                json.dump(res, jf, separators=(",", ":"))
            return
    else:
        assert args.file != None
    
    if not (args.collect_index or args.create_index):
        with open(args.html_key_idx) as jf:
            html_key_idx = json.load(jf)
        with open(args.html_name_idx) as jf:
            html_name_idx = json.load(jf)
        with open(args.css_ident_idx) as jf:
            css_ident_idx = json.load(jf)
    
    warnings.filterwarnings("ignore", category=bs4.MarkupResemblesLocatorWarning)
    with open(args.file) as file:
        content = file.read()
    res = None
    typ = None
    resp_len = len(content)
    if args.file.suffix == ".json":
        try:
            res = json.loads(content)
            typ = "json"
        except json.JSONDecodeError:
            write_error(args.file, "json")
            return
    elif args.file.suffix == ".html":
        soup = bs4.BeautifulSoup(content, "lxml")
        try:
            res = xml_children_to_dicts(soup)
            if res:
                typ = "html"
        except (AssertionError, RecursionError):
            write_error(args.file, "bs4")
            return
    elif args.file.suffix == ".css":
        try:
            css = tinycss2.parse_stylesheet(
                content,
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
            write_error(args.file, "css")
            return
    assert not content or (res and typ)
    if args.collect_index:
        if res:
            with sqlite3.connect(args.collect_index) as con:
                for typ in KEYS:
                    for key in KEYS[typ]:
                        cursor = con.execute(
                            "INSERT INTO keys(type, key, count) VALUES (?, ?, ?);",
                            (typ, key, KEYS[typ][key]),
                        )
                        key_id = cursor.lastrowid
                        if typ in SPECIAL_VALUES and key in SPECIAL_VALUES[typ]:
                            cursor = con.executemany(
                                """
                                INSERT INTO special_values(key_id, value, count)
                                    VALUES (?, ?, ?);
                                """,
                                [
                                    (key_id, value, SPECIAL_VALUES[typ][key][value])
                                    for value in SPECIAL_VALUES[typ][key]
                                ],
                            )
                con.commit()
    else:
        with open(f"{args.file}.cbor", "wb") as file:
            if not content:
                file.write(b"")
            elif typ == "json":
                cbor2.dump(res, file, canonical=True)
            elif typ == "css":
                file.write(encode_cbor_css(res, css_ident_idx))
            elif typ == "html":
                file.write(
                    encode_cbor_html(res, html_key_idx, html_name_idx, css_ident_idx)
                )


if __name__ == "__main__":
    main()
