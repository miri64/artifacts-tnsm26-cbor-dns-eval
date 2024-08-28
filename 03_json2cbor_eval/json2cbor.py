#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2023 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import base64
import concurrent.futures
import gzip
import json
import multiprocessing
import pathlib
import os
import re
import subprocess
import sys
import timeit
import traceback

import cbor2
import json5

SCRIPT_DIR = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))

INPUT_PATH = pathlib.Path(os.environ.get("INPUT_PATH", SCRIPT_DIR / "jsons"))
OUTPUT_PATH = pathlib.Path(os.environ.get("OUTPUT_PATH", SCRIPT_DIR / "cbors"))
JSON_TAXONOMY_PATH = pathlib.Path(os.environ.get("JSON_TAXONOMY_PATH", SCRIPT_DIR / "node_modules" / ".bin" / "json-taxonomy"))
GITHUB_PATH = INPUT_PATH / "github" / "github"
GITHUB_BLOBS_PATH = GITHUB_PATH / "blobs"
GITHUB_USERS_PATH = GITHUB_PATH / "users"
ITERATIONS = int(os.environ.get("ITERATIONS", 1000))


def output_path(json_filename, suffix):
    cbor_filename = OUTPUT_PATH / json_filename.relative_to(
        INPUT_PATH
    ).with_suffix("").with_suffix(suffix)
    cbor_filename.parent.mkdir(parents=True, exist_ok=True)
    return cbor_filename


def encode_cbor(json_filename, json_obj):
    # mark as encoded CBOR data item (see https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml)
    try:
        json_obj["content"] = cbor2.CBORTag(
            24, cbor2.dumps(json5.loads(json_obj["content"]), canonical=True)
        )

        cbor_filename = output_path(json_filename, ".cbor.cbor")
        with open(cbor_filename, "wb") as cbor_file:
            cbor2.dump(json_obj, cbor_file)
            size = cbor_file.tell()
        cbor_file.close()
        return size
    except (RecursionError, ValueError):
        return ""


def encode_binary(json_filename, json_obj):
    size = json_obj.pop("size")
    # mark as embedded JSON (see https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml)
    json_obj["content"] = base64.b64decode(json_obj["content"].value)

    assert len(json_obj["content"]) == size
    cbor_filename = output_path(json_filename, ".bin.cbor")
    with open(cbor_filename, "wb") as cbor_file:
        cbor2.dump(json_obj, cbor_file)
        return cbor_file.tell()


def tag_base64(json_filename, json_obj):
    encoding = json_obj.pop("encoding")
    assert encoding == "base64"
    # mark as base64 encoded (see https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml)
    json_obj["content"] = cbor2.CBORTag(34, json_obj["content"])

    cbor_filename = output_path(json_filename, ".b64tag.cbor")
    with open(cbor_filename, "wb") as cbor_file:
        cbor2.dump(json_obj, cbor_file)
        return cbor_file.tell()


def json_walk(json_obj):
    if isinstance(json_obj, dict):
        yield json_obj
        for key, value in json_obj.items():
            yield json_walk(key)
            yield json_walk(value)
    elif isinstance(json_obj, list):
        yield json_obj
        for value in json_obj:
            yield json_walk(value)
    elif isinstance(json_obj, cbor2.CBORTag):
        yield json_obj
        yield json_obj.value
    else:
        yield json_obj


def relative_to(json_filename, other):
    try:
        return isinstance(json_filename.relative_to(other), pathlib.Path)
    except ValueError:
        return False


def json_taxonomy(json_filename):
    if JSON_TAXONOMY_PATH.exists():
        try:
            out = subprocess.check_output([JSON_TAXONOMY_PATH, json_filename], text=True)
            tier, content_type, redundancy, structure = out.strip().split(", ")
            return int(tier.split()[1]), content_type, redundancy, structure
        except subprocess.CalledProcessError as exc:
            print(f"Cannot determine taxonony for {json_filename}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
    return "", "", "", ""


def compress(in_filename, out_filename):
    # gzip.open does not work with `with` in python 3.8.
    out_file = gzip.open(out_filename, "wb")
    try:
        with open(in_filename, "rb") as in_file:
            out_file.write(in_file.read())
    finally:
        out_file.close()
    return out_filename.stat().st_size


def convert2cbor(json_filename):
    cbor_base64_bin_size = ""
    cbor_base64_cbor_size = ""
    cbor_base64_cbor_gz_size = ""
    cbor_base64_tagged_size = ""
    github_type = "stored_json"
    try:
        size_tier, content_type, redundancy, structure = json_taxonomy(json_filename)
        cbor_simple_filename = output_path(json_filename, ".cbor")
        cbor_canon_filename = output_path(json_filename, ".canon.cbor")
        with \
            open(json_filename, encoding="utf-8") as json_file, \
            open(cbor_simple_filename, "wb") as cbor_simple_file, \
            open(cbor_canon_filename, "wb") as cbor_canon_file:

            json_obj = json.load(json_file)
            json_size = json_file.tell()
            json_elements = len([_ for _ in json_walk(json_obj)])
            cbor2.dump(json_obj, cbor_simple_file)
            cbor_simple_size = cbor_simple_file.tell()
            cbor2.dump(json_obj, cbor_canon_file, canonical=True)
            cbor_canon_size = cbor_canon_file.tell()
        json_file.close()
        cbor_simple_file.close()
        cbor_canon_file.close()

        json_gz_filename = output_path(json_filename, ".json.gz")
        json_gz_size = compress(json_filename, json_gz_filename)
        json_dumps_time = timeit.timeit(
            lambda: json.dumps(json_obj), number=ITERATIONS
        )
        json_enc = json.dumps(json_obj)
        json_loads_time = timeit.timeit(
            lambda: json.loads(json_enc), number=ITERATIONS
        )
        del json_enc

        cbor_simple_gz_filename = output_path(json_filename, ".cbor.gz")
        cbor_simple_gz_size = compress(cbor_simple_filename, cbor_simple_gz_filename)
        del cbor_simple_gz_filename
        del cbor_simple_filename
        cbor_dumps_time = timeit.timeit(
            lambda: cbor2.dumps(json_obj), number=ITERATIONS
        )
        cbor_enc = cbor2.dumps(json_obj)
        cbor_loads_time = timeit.timeit(
            lambda: cbor2.loads(cbor_enc), number=ITERATIONS
        )
        del cbor_enc
        cbor_canon_gz_filename = output_path(json_filename, ".canon.cbor.gz")
        cbor_canon_gz_size = compress(cbor_canon_filename, cbor_canon_gz_filename)
        del cbor_canon_gz_filename
        del cbor_canon_filename

        if relative_to(json_filename, GITHUB_BLOBS_PATH):
            cbor_base64_tagged_size = tag_base64(json_filename, json_obj)
            cbor_base64_bin_size = encode_binary(json_filename, json_obj)
            cbor_base64_cbor_size = encode_cbor(json_filename, json_obj)

            if cbor_base64_cbor_size:
                cbor_base64_cbor_filename = output_path(json_filename, ".cbor.cbor")
                cbor_base64_cbor_gz_filename = output_path(json_filename, ".cbor.cbor.gz")
                cbor_base64_cbor_gz_size = compress(
                    cbor_base64_cbor_filename, cbor_base64_cbor_gz_filename
                )

            github_type = "github_api_blob"
        elif relative_to(json_filename, GITHUB_USERS_PATH):
            github_type = "github_api_users"
        elif relative_to(json_filename, GITHUB_PATH):
            if (
                json_filename.parents[0].name == "searches"
                and relative_to(json_filename.parents[3], GITHUB_PATH)
            ):
                github_type = "github_api_repo_search"
            elif re.match(r"page\d+_since\d+.json", json_filename.name):
                github_type = "github_api_repos"
            else:
                github_type = "github_api_others"
        print(
            json_filename.relative_to(INPUT_PATH),
            json_filename.stat().st_mtime,
            github_type,
            size_tier,
            content_type,
            redundancy,
            structure,
            json_elements,
            json_size,
            json_gz_size,
            cbor_simple_size,
            cbor_simple_gz_size,
            cbor_canon_size,
            cbor_canon_gz_size,
            ITERATIONS,
            json_dumps_time,
            json_loads_time,
            cbor_dumps_time,
            cbor_loads_time,
            cbor_base64_tagged_size,
            cbor_base64_bin_size,
            cbor_base64_cbor_size,
            cbor_base64_cbor_gz_size,
            sep=";",
            flush=True,
        )
    except json.JSONDecodeError as exc:
        print(f"JSON error in {json_filename}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    except Exception as exc:
        print(f"PYTHON ERROR in {json_filename}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--header", action="store_true", help="Print CSV header")
    parser.add_argument("filename", nargs="?")
    args = parser.parse_args()
    if args.header:
        print(
            "json_filename",
            "json_mtime",
            "github_type",
            "json_size_tier",
            "json_content_type",
            "json_redundancy",
            "json_structure",
            "json_elements",
            "json_size",
            "json_gz_size",
            "cbor_simple_size",
            "cbor_simple_gz_size",
            "cbor_canon_size",
            "cbor_canon_gz_size",
            "iterations",
            "json_dumps_time",
            "json_loads_time",
            "cbor_dumps_time",
            "cbor_loads_time",
            "cbor_base64_tagged_size",
            "cbor_base64_bin_size",
            "cbor_base64_cbor_size",
            "cbor_base64_cbor_gz_size",
            sep=";",
            flush=True,
        )
        return
    # with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
    #     for root, dirs, filenames in os.walk(INPUT_PATH):
    root = INPUT_PATH.parent
    # filenames = sys.stdin
    # for filename in filenames:
    filename = args.filename.strip()
    if not filename.endswith(".cbor") and filename not in [
        "illegal_json.txt",
        "illegal_json_fixed.txt",
        "sha_filenames.csv",
    ]:
        # executor.submit(convert2cbor, pathlib.Path(root) / filename)
        convert2cbor(pathlib.Path(root) / filename)


if __name__ == "__main__":
    main()
