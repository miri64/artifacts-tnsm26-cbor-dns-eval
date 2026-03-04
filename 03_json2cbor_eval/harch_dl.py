#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024-26 TU Dresden
#
# Distributed under terms of the MIT license.

import sys
import json
import pathlib
import os
import urllib.parse

SCRIPT_DIR = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))

OUTPUT_PATH = pathlib.Path(
    os.environ.get("OUTPUT_PATH", SCRIPT_DIR / "jsons" / "harch")
)

if __name__ == "__main__":
    try:
        obj = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        sys.exit(1)
    url = sys.argv[1]
    url_path = urllib.parse.urlparse(sys.argv[1]).path
    if not url_path.endswith(".json"):
        url_path = f"{url_path}.json"
    path = OUTPUT_PATH / pathlib.Path(url_path.lstrip("/"))
    if path.name == ".json":
        path = path.parent / "index.json"
    if len(path.name) > 255:
        path = path.parent / f"{path.name[:246]}.json"
    counter = 0
    while path.exists():
        if counter == 0:
            path = path.parent / f"{'.'.join(path.name.split('.')[:-1])}.{counter:003d}.json"
        else:
            path = path.parent / f"{'.'.join(path.name.split('.')[:-2])}.{counter:003d}.json"
        counter += 1
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with open(path, "w") as json_file:
        json.dump(obj, json_file, separators=(",", ":"))
    print(url, path.relative_to(OUTPUT_PATH), sep="\t")
