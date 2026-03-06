#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import csv
import json
import pathlib
import re
import subprocess

import pprint


ARTIFACTS_CSV_FIELDNAMES = ["url", "mimeType", "resourceSize", "curlSize", "networkRequestTime", "networkEndTime", "rendererStartTime", "filename"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()

    run_path = pathlib.Path(args.run_dir)
    with open(run_path / "lhr.report.json") as f:
        obj = json.load(f)

    artifacts_path = run_path / "artifacts"
    if not artifacts_path.exists():
        artifacts_path.mkdir(parents=True)
    match = re.search(r"run-(\d+)", args.run_dir)
    with open(artifacts_path / f"artifacts-{match[0]}.csv", "w") as out_csv:
        out = csv.DictWriter(out_csv, fieldnames=ARTIFACTS_CSV_FIELDNAMES)
        out.writeheader()
        ls = []
        s = set()
        for item in obj["audits"]["network-requests"]["details"]["items"]:
            if item["resourceSize"] == 0:
                continue
            if item["mimeType"] in [
                "", "application/json", "text/css", "text/html", "text/plain"
            ]:
                proc = subprocess.Popen(
                    ["curl", "-A", obj["userAgent"], item["url"]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                output, _ = proc.communicate()
                item["curlSize"] = len(output)
                if item["mimeType"] in ["text/css", "text/html"]:
                    if item["mimeType"] == "text/css":
                        filename = f"{item['networkRequestTime']}.css"
                    elif item ["mimeType"] == "text/html":
                        filename = f"{item['networkRequestTime']}.html"
                    else:
                        assert False    
                    assert len(output) == item["resourceSize"], (
                        f"{item['mimeType']}:{item['url']}: "
                        f"{len(output)} != {item['resourceSize']}"
                    )
                    with open(artifacts_path / filename, "wb") as dump_file:
                        dump_file.write(output)
                else:
                    try:
                        json_obj = json.loads(output)
                    except UnicodeDecodeError:
                        continue
                    except json.JSONDecodeError:
                        continue
                    filename = f"{item['networkRequestTime']}.json"
                    with open(artifacts_path / filename, "wt") as dump_file:
                        json.dump(json_obj, dump_file, separators=(',', ':'))
                item["filename"] = filename
                out.writerow(
                    {k: v for k, v in item.items() if k in ARTIFACTS_CSV_FIELDNAMES}
                )
    assert len(s) == len(ls)
