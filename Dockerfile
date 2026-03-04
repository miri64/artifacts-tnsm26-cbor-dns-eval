# Copyright (C) 2025 TU Dresden
#
# Distributed under terms of the MIT license.

FROM python:3.12-trixie

WORKDIR /app

ARG HOST_UID
ARG HOST_GID
RUN addgroup --gid "$HOST_GID" user || true  # just use group if it already exists
RUN addgroup wireshark || true  # just use group if it already exists
RUN adduser --disabled-password --home /home/user/ --shell /bin/bash user --uid "$HOST_UID" --gid "$HOST_GID" && usermod -a -G wireshark user && chown -R user:user /home/user 

# in case clang-14 is needed, we might need to go back to bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libbz2-dev \
    libffi-dev \
    libgdbm-dev \
    libgdbm-compat-dev \
    liblzma-dev \
    libncurses5-dev \
    libreadline6-dev \
    libsqlite3-dev \
    libssl-dev \
    lzma \
    moreutils \
    tk-dev \
    uuid-dev \
    zlib1g-dev \
    poppler-utils \
    cm-super \
    dvipng \
    texlive-fonts-extra \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-plain-generic \
    texlive-pictures \
    texlive-xetex \
    npm \
    parallel \
    pigz \
    tmux \
    tshark

RUN setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap && \
   chown root:wireshark /usr/bin/dumpcap && chmod u+s /usr/bin/dumpcap && chmod o-rx /usr/bin/dumpcap 

COPY requirements.txt ./
RUN pip --no-cache-dir install --upgrade uv && \
    uv pip --no-cache-dir install --system --upgrade -r requirements.txt
