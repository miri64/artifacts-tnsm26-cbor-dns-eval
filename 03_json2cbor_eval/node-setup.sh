#! /bin/bash
#
# node-setup.sh
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

set -x
cd ${SCRIPT_DIR}
npm install  @sourcemeta/json-taxonomy
set +x
