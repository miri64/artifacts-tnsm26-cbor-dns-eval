#! /bin/sh
#
# ubuntu-setup.sh
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

set -x
sudo DEBIAN_FRONTEND=noninteractive apt-get -y update
sudo DEBIAN_FRONTEND=noninteractive apt-get -y dist-upgrade curl git parallel pigz tshark \
    npm python3-pip python3-virtualenv python3-dev \
    libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
    libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
    lzma lzma-dev tk-dev uuid-dev zlib1g-dev poppler-utils \
    cm-super dvipng texlive-fonts-extra texlive-latex-extra texlive-pictures texlive-xetex
yes | sudo DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common
sudo usermod -a -G wireshark ${USER}
set +x
