#!/usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import re
import os
import pathlib
import subprocess
import sys


SCRIPT_DIR = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
DOMAIN_LIST_DATA = SCRIPT_DIR / "v2fly-domain-list-community" / "data"
REGEXES = {}
DOMAINS = {}


def categories_from_file(root, filename, category=None):
    if not category:
        category = filename
    with open(root / filename) as domain_file:
        for line in domain_file:
            line = line.strip()
            line = re.sub(r"\s*#.*$", "", line)
            if not line or line.startswith("keyword:"):
                continue
            elif line.startswith("regexp:"):
                key = re.compile(":".join(line.split(":")[1:]))
                if key in REGEXES:
                    REGEXES[key].add(category)
                else:
                    REGEXES[key] = set([category])
                return
            elif line.startswith("include:"):
                line = line[len("include:"):]
                categories_from_file(root, line, filename)
            elif line.startswith("domain:"):
                line = line[len("domain:"):]
            elif line.startswith("full:"):
                line = line[len("full:"):]
            line = re.sub(r"(\s*@[^\s]+)+$", "", line)
            if line in DOMAINS:
                DOMAINS[line].add(category)
            else:
                DOMAINS[line] = set([category])


def create_category_dicts(prepare=False):
    for root, dirs, files in os.walk(DOMAIN_LIST_DATA):
        for filename in files:
            categories_from_file(pathlib.Path(root), filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--header", action="store_true")
    args = parser.parse_args()
    reader = csv.reader(sys.stdin)
    if args.header:
        row = next(reader)
        print(*row[0:6], "categories", *row[6:], sep=";")
        sys.exit(0)
    create_category_dicts()
    writer = csv.writer(sys.stdout, delimiter=";")
    for row in reader:
        if row[6] == "count":
            continue
        row_categories = set()
        for key in REGEXES:
            if key.match(row[5]):
                row_categories.update(REGEXES[key])
        for key in DOMAINS:
            if row[5] == key or row[5].endswith(f".{key}"):
                row_categories.update([cat for cat in DOMAINS[key] if row[5] == key or not re.search(r"\btld\b", cat)])
        writer.writerow(row[0:6] + [list(sorted(row_categories))] + row[6:])
