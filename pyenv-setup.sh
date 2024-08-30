#! /bin/bash
#
# pyenv-setup.sh
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

export PYENV_ROOT="${HOME}/.pyenv"
if ! [ -d "${PYENV_ROOT}" ]; then
    git clone https://github.com/pyenv/pyenv.git "${PYENV_ROOT}"
fi
if ! [ -d "${PYENV_ROOT}/plugins/pyenv-virtualenv" ]; then
    git clone https://github.com/pyenv/pyenv-virtualenv.git "${PYENV_ROOT}/plugins/pyenv-virtualenv"
fi
echo 'export PYENV_ROOT="${HOME}/.pyenv"' >> "${HOME}/.bashrc"
echo 'command -v pyenv >/dev/null || export PATH="${PYENV_ROOT}/bin:${PATH}"' >> "${HOME}/.bashrc"
echo 'eval "$(pyenv init -)"' >> "${HOME}/.bashrc"

command -v pyenv >/dev/null || export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init -)"
pyenv install 3.12.5
pyenv global 3.12.5
pyenv virtualenv cbor-dns-eval-tbd
pyenv activate cbor-dns-eval-tbd
pip install -r "${SCRIPT_DIR}/requirements.txt" --upgrade

for nb in "${SCRIPT_DIR}"/*.ipynb "${SCRIPT_DIR}"/0[0-9A]_*/*.ipynb; do
    jupyter trust "${nb}"
done
