#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright (C) 2023 TU Dresden
#
# Distributed under terms of the MIT license.


import argparse
import base64
import functools
import itertools
import json

import cbor2


def values(obj):
    if isinstance(obj, dict):
        return list(obj.values())
    elif isinstance(obj, list):
        return obj
    else:
        []


class EncodeCBORDict(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode()
        elif isinstance(obj, cbor2.CBORTag):
            return obj.value
        return super().default(obj)


def utf8size(obj):
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), cls=EncodeCBORDict))


def byte_size(obj):
    if isinstance(obj, (dict, list)):
        return functools.reduce(
            lambda acc, size: {
                "scalar": acc["scalar"] + size["scalar"],
                "structural": acc["structural"] + size["structural"],
            },
            list(
                map(
                    byte_size,
                    values(obj),
                )
            )
            + [
                {
                    "scalar": 0,
                    "structural": (
                        (2 + max(len(obj), 1) - 1)
                        if isinstance(obj, list)
                        else len(obj.keys()) + utf8size(list(obj.keys()))
                    ),
                }
            ],
            {"scalar": 0, "structural": 0},
        )
    return {"scalar": utf8size(obj), "structural": 0}


def deep_values(obj):
    if isinstance(obj, (dict, list)):
        return functools.reduce(
            lambda acc, el: acc + deep_values(el), values(obj), [obj]
        )
    return [obj]


def height(obj):
    if isinstance(obj, (dict, list)):
        return 1 + max([0] + list(map(height, values(obj))))
    return 0


def level(obj, lvl):
    if lvl == 0:
        return [obj]
    elif isinstance(obj, (dict, list)):
        if lvl <= 1:
            return list(
                filter(
                    lambda el: not isinstance(el, (dict, list)),
                    values(obj),
                )
            )
        else:
            return functools.reduce(
                lambda acc, el: acc + level(el, lvl - 1),
                values(obj),
                [],
            )
    else:
        return []


def acc_byte_size(elements, size_keys=["scalar", "structural"]):
    return functools.reduce(
        lambda acc, size: acc + sum(size[k] for k in size_keys),
        map(lambda el: byte_size(el), elements),
        0,
    )


def level_analyze(obj, lvl):
    elements = level(obj, lvl)
    return {
        "count": len(elements),
        "size": acc_byte_size(elements),
    }


def is_deep_equal(left, right):
    if isinstance(left, cbor2.CBORTag):
        if not isinstance(right, cbor2.CBORTag):
            return False
        return left == right
    if isinstance(left, dict):
        if not isinstance(right, dict):
            return False
        elif len(left) != len(right):
            return False

        for key in left:
            if key not in right or not is_deep_equal(left[key], right[key]):
                return False

        return True
    elif isinstance(left, list):
        if not isinstance(right, list):
            return False
        elif len(left) != len(right):
            return False

        for index, value in enumerate(left):
            if not is_deep_equal(value, right[index]):
                return False

        return True
    return left == right


def unique_deep(objs):
    return functools.reduce(
        lambda acc, el: (
            acc + [el] if not any(is_deep_equal(item, el) for item in acc) else acc
        ),
        objs,
        []
    )


def analyze(obj):
    byte_sz = byte_size(obj)
    values = deep_values(obj)
    higt = height(obj)

    textual = list(filter(lambda el: isinstance(el, str), values))
    binary = list(filter(lambda el: isinstance(el, bytes), values))
    numeric = list(filter(lambda el: isinstance(el, (int, float)) or (isinstance(el, cbor2.CBORSimpleValue) and ((el.value >= 16 and el.value < 20) or el.value > 23)), values))
    boolean = list(filter(lambda el: isinstance(el, (bool) or (el is None)), values))
    taggy = list(filter(lambda el: isinstance(el, cbor2.CBORTag) or (isinstance(el, cbor2.CBORSimpleValue) and el.value < 16), values))
    structural = list(filter(lambda el: isinstance(el, (dict, list)), values))

    return {
        "size": byte_sz["scalar"] + byte_sz["structural"],
        "count": len(values),
        "height": higt,
        "levels": list(map(lambda lvl: level_analyze(obj, lvl), range(higt + 1))),
        "values": {
            "textual": {
                "count": len(textual),
                "duplicates": len(textual) - len(set(textual)),
                "size": acc_byte_size(textual, ["scalar"]),
            },
            "binary": {
                "count": len(binary),
                "duplicates": len(binary) - len(set(binary)),
                "size": acc_byte_size(binary, ["scalar"]),
            },
            "numeric": {
                "count": len(numeric),
                "duplicates": len(numeric) - len(set(numeric)),
                "size": acc_byte_size(numeric, ["scalar"]),
            },
            "boolean": {
                "count": len(boolean),
                "duplicates": len(boolean) - len(set(boolean)),
                "size": acc_byte_size(boolean, ["scalar"]),
            },
            "taggy": {
                "count": len(taggy),
                "duplicates": len(taggy) - len(unique_deep(taggy)),
                "size": acc_byte_size(taggy, ["scalar"]),
            },
            "structural": {
                "count": len(structural),
                "duplicates": len(structural) - len(unique_deep(structural)),
                "size": acc_byte_size(structural, ["scalar"]),
            },
        },
    }


def percentage(total, local):
    return 0 if total == 0 else local * 100 / total


def main(obj):
    if isinstance(obj, str):
        return ["str", "str", "str", "str"]
    analysis = analyze(obj)
    qualifiers = []

    if analysis["size"] < 100:
        qualifiers.append("tier 1")
    elif analysis["size"] < 1000:
        qualifiers.append("tier 2")
    else:
        qualifiers.append("tier 3")

    textual_weight = (
        analysis["values"]["textual"]["count"] * analysis["values"]["textual"]["size"]
    )
    binary_weight = (
        analysis["values"]["binary"]["count"] * analysis["values"]["binary"]["size"]
    )
    numeric_weight = (
        analysis["values"]["numeric"]["count"] * analysis["values"]["numeric"]["size"]
    )
    boolean_weight = (
        analysis["values"]["boolean"]["count"] * analysis["values"]["boolean"]["size"]
    )
    taggy_weight = (
        analysis["values"]["taggy"]["count"] * analysis["values"]["taggy"]["size"]
    )

    if (
        textual_weight == 0
        and binary_weight == 0
        and numeric_weight == 0
        and boolean_weight == 0
        and taggy_weight == 0
    ):
        qualifiers.append("structural")
    elif (
        binary_weight >= textual_weight
        and binary_weight >= numeric_weight
        and binary_weight >= boolean_weight
        and binary_weight >= taggy_weight
    ):
        qualifiers.append("binary")
    elif (
        textual_weight >= binary_weight
        and textual_weight >= numeric_weight
        and textual_weight >= boolean_weight
        and textual_weight >= taggy_weight
    ):
        qualifiers.append("textual")
    elif (
        numeric_weight >= binary_weight
        and numeric_weight >= textual_weight
        and numeric_weight >= boolean_weight
        and numeric_weight >= taggy_weight
    ):
        qualifiers.append("numeric")
    elif (
        boolean_weight >= binary_weight
        and boolean_weight >= textual_weight
        and boolean_weight >= numeric_weight
        and boolean_weight >= taggy_weight
    ):
        qualifiers.append("boolean")
    elif (
        taggy_weight >= binary_weight
        and taggy_weight >= textual_weight
        and taggy_weight >= numeric_weight
        and taggy_weight >= boolean_weight
    ):
        qualifiers.append("taggy")

    duplicates = (
        analysis["values"]["textual"]["duplicates"]
        + analysis["values"]["binary"]["duplicates"]
        + analysis["values"]["numeric"]["duplicates"]
        + analysis["values"]["boolean"]["duplicates"]
        + analysis["values"]["taggy"]["duplicates"]
        + analysis["values"]["structural"]["duplicates"]
    )
    if percentage(analysis["count"], duplicates) >= 25:
        qualifiers.append("redundant")
    else:
        qualifiers.append("non-redundant")

    try:
        largest_level = sorted(
            map(
                lambda lvl: {**{"index": lvl[0] + 1}, **lvl[1]},
                enumerate(analysis["levels"][1:]),
            ),
            key=lambda k: (k["size"], k["index"]),
            reverse=True,
        )[0]
    except IndexError:
        largest_level = {**{"index": 0}, **analysis["levels"][0]}
    if (
        textual_weight == 0
        and binary_weight == 0
        and numeric_weight == 0
        and boolean_weight == 0
        and taggy_weight == 0
        and analysis["height"] >= 5
    ):
        qualifiers.append("nested")
    elif (analysis["height"] * largest_level["index"]) >= 10:
        qualifiers.append("nested")
    else:
        qualifiers.append("flat")
    return qualifiers


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_filename")
    args = parser.parse_args()
    with open(args.json_filename) as json_file:
        print(main(json.load(json_file)))
