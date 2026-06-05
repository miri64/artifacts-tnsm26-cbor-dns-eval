# Copyright (C) 2025 TU Dresden
#
# Distributed under terms of the MIT license.

FROM python:3.12-trixie

WORKDIR /app

ARG HOST_UID
ARG HOST_GID
RUN addgroup --gid "$HOST_GID" user || true  # just use group if it already exists
RUN addgroup wireshark || true  # just use group if it already exists
RUN adduser --disabled-password --home /home/user/ --shell /bin/bash user --uid "$HOST_UID" --gid "$HOST_GID" && usermod -a -G wireshark user && chown -R "$HOST_UID:$HOST_GID" /home/user 

# in case clang-14 is needed, we might need to go back to bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gawk \
    git \
    iproute2 \
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

ARG ARM_URLBASE=https://developer.arm.com/-/media/Files/downloads/gnu-rm
ARG ARM_URL=${ARM_URLBASE}/10.3-2021.10/gcc-arm-none-eabi-10.3-2021.10-x86_64-linux.tar.bz2
ARG ARM_MD5=2383e4eb4ea23f248d33adc70dc3227e
ARG ARM_FOLDER=gcc-arm-none-eabi-10.3-2021.10
RUN echo 'Installing arm-none-eabi toolchain from arm.com' >&2 && \
    mkdir -p /opt && \
    curl -L -o /opt/gcc-arm-none-eabi.tar.bz2 ${ARM_URL} && \
    echo "${ARM_MD5} /opt/gcc-arm-none-eabi.tar.bz2" | md5sum -c && \
    tar -C /opt -jxf /opt/gcc-arm-none-eabi.tar.bz2 && \
    rm -f /opt/gcc-arm-none-eabi.tar.bz2 && \
    echo 'Removing documentation' >&2 && \
    rm -rf /opt/gcc-arm-none-eabi-*/share/doc

ENV PATH ${PATH}:/opt/${ARM_FOLDER}/bin
RUN echo 'export PATH=${PATH}:'"/opt/${ARM_FOLDER}/bin" >> /home/user/.profile
