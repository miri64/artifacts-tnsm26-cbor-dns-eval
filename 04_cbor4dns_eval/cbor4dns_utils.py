#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.

import collections
import csv
import os.path

import dns.name


class ThreadSafeDict(dict):
    def __init__(self, manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = manager.RLock()

    def __contains__(self, key):
        with self._lock:
            return super().__contains__(key)

    def __delitem__(self, key):
        with self._lock:
            return super().__delitem__(key)

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        with self._lock:
            return super().__setitem__(key, value)


class EmptyingDict(collections.OrderedDict):
    MAX_ITEMS = 700000

    def __init__(self, manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = manager.RLock()

    def __setitem__(self, key, value):
        with self._lock:
            if len(self) >= self.MAX_ITEMS:
                self.popitem(last=False)
            return super().__setitem__(key, value)

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)

    def __contains__(self, key):
        with self._lock:
            return super().__contains__(key)


class FlushableThreadSafeDictWriter(csv.DictWriter):
    def __init__(self, file, manager, *args, **kwargs):
        super().__init__(file, *args, **kwargs)
        self._file = file
        self._lock = manager.RLock()

    def writeheader(self):
        with self._lock:
            super().writeheader()
            self._file.flush()

    def writerow(self, row):
        with self._lock:
            super().writerow(row)
            self._file.flush()

    def writerows(self, rows):
        with self._lock:
            super().writerows(rows)
            self._file.flush()


def decode_name(name):
    return dns.name.from_text(name).to_text(omit_final_dot=True)


def common_suffixes(name1, name2):
    return (
        len(os.path.commonprefix([name1[::-1], name2[::-1]])),
        len(
            ".".join(
                os.path.commonprefix(
                    [
                        name1[::-1].split("."),
                        name2[::-1].split("."),
                    ]
                )
            )
        )
        + 1,  # add leading delimiter
    )
