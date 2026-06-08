#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import argparse
import sqlite3
import urllib.parse

import dns.message
import dns.query

from scapy.all import DNS as ScapyDNS


def fetch_record(upstream_doh, con, hostname, qtype):
    cur = con.execute(
        """
        SELECT resp FROM dns_responses WHERE name = ? AND type = ?
        """,
        (hostname, qtype)
    )
    res = cur.fetchone()
    if res is None:
        dns_query = dns.message.make_query(hostname, qtype)
        dns_resp = dns.query.https(dns_query, upstream_doh)
        scapy_resp = ScapyDNS(dns_resp.to_wire())
        if scapy_resp.an:
            for i in range(scapy_resp.ancount):
                if scapy_resp.an[i].rclass != 1:
                    continue
                if scapy_resp.an[i].type == 1:
                    scapy_resp.an[i].ttl = 0
                    scapy_resp.an[i].rdata = "127.0.0.1"
                elif scapy_resp.an[i].type == 28:
                    scapy_resp.an[i].ttl = 0
                    scapy_resp.an[i].rdata = "::1"
            scapy_resp.id = 0
            res = dns.message.from_wire(bytes(scapy_resp)).to_text()
        while True:
            try:
                con.execute(
                    "INSERT INTO dns_responses (name, type, resp) VALUES (?, ?, ?)",
                    (hostname, qtype, res),
                )
                con.commit()
                break
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode != 5:
                    raise
            except sqlite3.IntegrityError:
                break
        return res
    else:
        return res[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_doh")
    parser.add_argument("database")
    parser.add_argument("url")
    args = parser.parse_args()

    with sqlite3.connect(args.database) as con:
        while True:
            try:
                con.execute("pragma journal_mode = WAL;")
                con.execute("pragma foreign_keys = ON;")
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dns_responses (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        type INTEGER NOT NULL,
                        resp TEXT DEFAULT NULL,
                        UNIQUE(name, type)
                    );
                    """
                )
                con.execute(
                    "CREATE INDEX IF NOT EXISTS name_idx ON dns_responses(name, type);"
                )
                con.commit()
                break
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode != 5:
                    raise
        parts = urllib.parse.urlparse(args.url)
        fetch_record(args.upstream_doh, con, parts.hostname, 1)
        fetch_record(args.upstream_doh, con, parts.hostname, 28)




if __name__ == "__main__":
    main()
