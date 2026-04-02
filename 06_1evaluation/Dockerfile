FROM python:3.12-slim-trixie

ARG MODULE_NAME
ARG MODULE_SRC
ENV MODULE_NAME=ngx_http_replace_cbor_module
ENV MODULE_SRC=ngx-http-replace-cbor-module
ENV NGINX_VER=${NGINX_VER:-nginx-1.26.3}

WORKDIR /app

RUN sed -i 's/Types: *deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources && \
    apt update && apt install -y --no-install-recommends \
    build-essential libpcre2-dev libssl-dev zlib1g-dev libgd-dev curl procps && \
    cd /usr/local/src/ && apt source nginx=1.26.3-3+deb13u2

COPY "./${MODULE_SRC}" "/usr/local/src/${NGINX_VER}/${MODULE_SRC}"
COPY "./build_nginx.sh" /usr/local/src/"${NGINX_VER}"
RUN cd /usr/local/src/"${NGINX_VER}" && ./build_nginx.sh #&& \
    # mkdir -p "$(nginx -V 2>&1 | sed -n 's/.*--modules-path=\([a-z\/]*\).*/\1/p')" && \
    # cp "/usr/local/src/${NGINX_VER}/objs/${MODULE_NAME}.so" \
    #     "$(nginx -V 2>&1 | sed -n 's/.*--modules-path=\([a-z\/]*\).*/\1/p')"
RUN pip install "/usr/local/src/${NGINX_VER}/${MODULE_SRC}"
