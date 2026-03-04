#! /usr/bin/env python3
#
# Copyright (C) 2023-26 TU Dresden
#
# Distributed under terms of the MIT license.

import base64
import json
import http.client
import pathlib
import pprint
import re
import os
import time
import urllib.parse

import agithub.GitHub
import json5

SCRIPT_PATH = pathlib.Path(__file__).resolve().parent
OUTPUT_PATH = pathlib.Path(os.environ.get("OUTPUT_PATH", SCRIPT_PATH)).resolve()
GITHUB_PATH = OUTPUT_PATH / "jsons" / "github"
PER_PAGE = 100


class JSON5DecodeError(Exception):
    pass


class AlreadyDownloaded(Exception):
    pass


def page_ref_by_rel(headers, rel):
    try:
        match = re.search(rf"<([^>]+)>; rel=\"{rel}\"", headers["Link"])
    except KeyError:
        return None
    if not match:
        return None
    url = urllib.parse.urlparse(match[1])
    queries = urllib.parse.parse_qs(url.query)
    queries = {k: v[0] for k, v in queries.items()}
    return queries


def page_ref(headers):
    return page_ref_by_rel(headers, "next")


def prepare():
    with open(SCRIPT_PATH / ".gh_token") as token_file:
        token = token_file.readline().strip()
    return agithub.GitHub.GitHub(token=token)


def store_json(path: pathlib.Path, name: str, obj: dict | list):
    if not path.exists():
        path.mkdir(parents=True)
    try:
        with open(path / name, "w", encoding="utf-8") as json_file:
            json.dump(obj, json_file, ensure_ascii=False, separators=(",", ":"))
    except UnicodeEncodeError:
        (path / name).unlink()
        raise


def default_queries(queries):
    return {
        "page": queries.get("page", 1),
        "per_page": queries.get("per_page", 30),
        "since": queries.get("since", 0),
    }


def users(github):
    queries = {"per_page": PER_PAGE}
    while queries is not None:
        status = 500
        while status // 100 == 5 or status == 408:
            try:
                status, users = github.users.get(**queries)
            except (ConnectionResetError, TimeoutError):
                time.sleep(5)
                continue
            if status // 100 == 5 or status == 408:
                time.sleep(10)
            elif status != 200:
                raise http.client.HTTPException(
                    f"Error status {status} for users {queries}"
                )
        store_json(
            GITHUB_PATH / "github" / "users",
            "page{page}_since{since}.json".format(**default_queries(queries)),
            users,
        )
        queries = page_ref(dict(github.getheaders()))
        for user in users:
            yield user


def repos(github, user):
    queries = {"per_page": PER_PAGE}
    while queries is not None:
        status = 500
        while status // 100 == 5 or status == 408:
            try:
                status, repos = github.get(url=user["repos_url"], **queries)
            except (ConnectionResetError, TimeoutError):
                time.sleep(5)
                continue
            if status // 100 == 5 or status == 408:
                time.sleep(10)
            elif status != 200:
                raise http.client.HTTPException(
                    f"Error status {status} for repos {queries}"
                )
        if repos:
            store_json(
                GITHUB_PATH / "github" / user["login"],
                "page{page}_since{since}.json".format(**default_queries(queries)),
                repos,
            )
        queries = page_ref(dict(github.getheaders()))
        for repo in repos:
            yield repo


def get_git_blob(github, item, sha_filenames):
    blobs_path = GITHUB_PATH / "github" / "blobs"
    org, repo = item["repository"]["full_name"].split("/")
    name = item["name"]
    path = item["path"].split("/")
    json_path = GITHUB_PATH / org / repo / pathlib.Path(*path[:-1])
    sha = item["sha"]
    print(
        sha,
        str((json_path / name).relative_to(OUTPUT_PATH)),
        sep=";",
        file=sha_filenames
    )
    if (blobs_path / f"{sha}.json").exists():
        raise AlreadyDownloaded()
    status = 500
    while status // 100 == 5 or status == 408:
        try:
            status, git_blob = github.get(url=item["git_url"])
        except (ConnectionResetError, TimeoutError):
            time.sleep(5)
            continue
        if status // 100 == 5 or status == 408:
            time.sleep(10)
        elif status != 200:
            raise http.client.HTTPException(
                f"Error status {status} for {item['git_url']} to {json_path / name}"
            )

    store_json(blobs_path, f"{sha}.json", git_blob)
    assert git_blob["encoding"] == "base64"
    try:
        json_str = base64.b64decode(git_blob["content"]).decode(encoding="utf-8")
        return json_path, name, json5.loads(json_str)
    except (RecursionError, ValueError) as e:
        raise JSON5DecodeError(e) from e


def search_repo(github, repo):
    queries = {"per_page": PER_PAGE}
    q = f"language:json repo:{repo['full_name']}"
    search_path = (
        GITHUB_PATH
        / "github"
        / pathlib.Path(*repo["full_name"].split("/"))
        / "searches"
    )
    while queries is not None:
        status = 500
        queries.pop("q", None)
        while status // 100 == 5 or status == 408:
            try:
                status, search_data = github.search.code.get(q=q, **queries)
            except (ConnectionResetError, TimeoutError):
                time.sleep(5)
                continue
            if status // 100 == 5 or status == 408:
                time.sleep(10)
            elif status != 200:
                raise http.client.HTTPException(
                    f"Error status {status} for users search q={q} {queries}"
                )
        if search_data["total_count"] > 0:
            store_json(
                search_path,
                "page{page}_since{since}.json".format(**default_queries(queries)),
                search_data,
            )
        queries = page_ref(dict(github.getheaders()))
        for item in search_data["items"]:
            yield item


def main():
    github = prepare()
    if not GITHUB_PATH.exists():
        GITHUB_PATH.mkdir(parents=True)
    if not (GITHUB_PATH / "github").exists():
        (GITHUB_PATH / "github").mkdir(parents=True)
    with (
        open(
            GITHUB_PATH / "illegal_json.txt", "w", encoding="utf-8"
        ) as illegal_jsons,
        open(
            GITHUB_PATH / "github" / "sha_filenames.csv", "w", encoding="utf-8"
        ) as sha_filenames,
    ):
        print("url", "error", sep=";", file=illegal_jsons)
        print("sha", "filename", sep=";", file=sha_filenames)
        for user in users(github):
            for repo in repos(github, user):
                for item in search_repo(github, repo):
                    try:
                        store_json(*get_git_blob(github, item, sha_filenames))
                    except AlreadyDownloaded:
                        continue
                    except JSON5DecodeError:
                        print(
                            item["html_url"],
                            "not_parsable",
                            sep=";",
                            file=illegal_jsons
                        )
                        continue
                    except UnicodeEncodeError:
                        print(
                            item["html_url"],
                            "not_utf8",
                            sep=";",
                            file=illegal_jsons
                        )
                        continue


if __name__ == "__main__":
    main()
