#!/bin/sh
#
# jupyter-service-setup.sh
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

export NAME=jupyter

set -x
# Create service file
# TBD needs to be fixed once repo is published
cat >/etc/systemd/system/"${NAME}".service <<EOF
[Unit]
Description=${NAME}

[Service]
Type=simple
ExecStart=bash -c "source /home/vagrant/.pyenv/versions/cbor-dns-eval-tbd/bin/activate; /home/vagrant/.pyenv/versions/cbor-dns-eval-tbd/bin/jupyter lab --ip 0.0.0.0 --LabApp.token=''"

WorkingDirectory=/home/vagrant/cbor-dns-eval-tbd
User=vagrant
Group=vagrant

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl enable --now "${NAME}"
set +x
